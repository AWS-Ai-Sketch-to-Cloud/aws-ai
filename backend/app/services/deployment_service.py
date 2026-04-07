from __future__ import annotations

from collections.abc import Callable
import os
from queue import Empty, Queue
import shutil
import subprocess
from threading import Thread
import time
from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError


@dataclass
class DeployExecutionResult:
    status: str
    log: str
    resources: dict[str, object] | None = None


@dataclass
class AwsCredentials:
    access_key_id: str
    secret_access_key: str
    session_token: str | None


def _resolve_terraform_bin() -> str:
    env_bin = os.getenv("TERRAFORM_BIN", "").strip()
    if env_bin:
        return env_bin

    path_bin = shutil.which("terraform")
    if path_bin:
        return path_bin

    winget_bin = Path(
        os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Hashicorp.Terraform_Microsoft.Winget.Source_8wekyb3d8bbwe\terraform.exe"
        )
    )
    if winget_bin.exists():
        return str(winget_bin)

    return "terraform"


def _allowed_regions() -> set[str]:
    raw = os.getenv("DEPLOY_ALLOWED_REGIONS", "ap-northeast-2,ap-northeast-1,us-east-1")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _allowed_account_ids() -> set[str]:
    raw = os.getenv("DEPLOY_ALLOWED_ACCOUNT_IDS", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _max_resource_count() -> int:
    try:
        return max(1, int(os.getenv("DEPLOY_MAX_RESOURCE_COUNT", "25")))
    except ValueError:
        return 25


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _terraform_init_timeout_sec() -> int:
    return _int_env("DEPLOY_TERRAFORM_INIT_TIMEOUT_SEC", 900, minimum=60)


def _terraform_apply_timeout_sec() -> int:
    return _int_env("DEPLOY_TERRAFORM_APPLY_TIMEOUT_SEC", 5400, minimum=60)


def _terraform_destroy_timeout_sec() -> int:
    return _int_env("DEPLOY_TERRAFORM_DESTROY_TIMEOUT_SEC", 7200, minimum=60)


def _estimate_resource_count(terraform_code: str) -> int:
    return terraform_code.count('resource "')


def _guardrails_check(terraform_code: str, region: str) -> None:
    if region not in _allowed_regions():
        raise ValueError(f"region not allowed: {region}")
    count = _estimate_resource_count(terraform_code)
    if count > _max_resource_count():
        raise ValueError(f"resource count limit exceeded: {count}>{_max_resource_count()}")


def _run(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_sec: int = 300,
    on_output: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        return 127, f"{cmd[0]} command not found. Install Terraform and ensure it is in PATH."

    output_lines: list[str] = []
    line_queue: Queue[str | None] = Queue()
    start_at = time.monotonic()
    stdout = proc.stdout

    def _reader() -> None:
        if stdout is None:
            line_queue.put(None)
            return
        try:
            for raw in iter(stdout.readline, ""):
                line_queue.put(raw.rstrip("\r\n"))
        finally:
            line_queue.put(None)

    reader_thread = Thread(target=_reader, daemon=True)
    reader_thread.start()

    while True:
        try:
            line = line_queue.get(timeout=0.3)
            if line is None:
                break
            output_lines.append(line)
            if on_output:
                on_output(line)
        except Empty:
            if time.monotonic() - start_at > timeout_sec:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                timeout_msg = f"command timed out after {timeout_sec} seconds: {' '.join(cmd)}"
                output_lines.append(timeout_msg)
                if on_output:
                    on_output(timeout_msg)
                return 124, "\n".join(output_lines).strip()
            if proc.poll() is not None and line_queue.empty():
                break

    return proc.wait(), "\n".join(output_lines).strip()


def _state_root_dir() -> Path:
    configured = os.getenv("DEPLOY_STATE_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "storage" / "deploy-state"


def _session_work_dir(state_key: str) -> Path:
    safe_key = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in state_key).strip("._")
    if not safe_key:
        raise ValueError("state key is required")
    return _state_root_dir() / safe_key


def _state_file_paths(work_dir: Path) -> list[Path]:
    return [
        work_dir / "terraform.tfstate",
        work_dir / "terraform.tfstate.backup",
        work_dir / ".terraform.lock.hcl",
    ]


def _prepare_work_dir(*, terraform_code: str, state_key: str) -> tuple[Path, bool]:
    work_dir = _session_work_dir(state_key)
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "main.tf").write_text(terraform_code, encoding="utf-8")
    state_exists = (work_dir / "terraform.tfstate").exists()
    return work_dir, state_exists


def _clear_saved_state(work_dir: Path) -> None:
    for file_path in _state_file_paths(work_dir):
        if file_path.exists():
            file_path.unlink()
    _cleanup_runtime_artifacts(work_dir)


def _cleanup_runtime_artifacts(work_dir: Path) -> None:
    lock_file = work_dir / ".terraform.lock.hcl"
    if lock_file.exists():
        lock_file.unlink()
    terraform_dir = work_dir / ".terraform"
    if terraform_dir.exists():
        shutil.rmtree(terraform_dir, ignore_errors=True)


def _build_state_metadata(*, work_dir: Path, state_exists_before: bool, destroyed: bool = False) -> dict[str, object]:
    state_file = work_dir / "terraform.tfstate"
    return {
        "stateDir": str(work_dir),
        "stateFile": str(state_file),
        "statePreserved": state_file.exists() and not destroyed,
        "stateExistedBefore": state_exists_before,
    }


def _assume_role(
    *,
    role_arn: str,
    role_session_name: str,
    region: str,
    external_id: str | None = None,
) -> AwsCredentials:
    client = boto3.client("sts", region_name=region)
    params: dict[str, str] = {"RoleArn": role_arn, "RoleSessionName": role_session_name}
    if external_id:
        params["ExternalId"] = external_id
    try:
        response = client.assume_role(**params)
    except (BotoCoreError, ClientError) as e:
        raise ValueError(f"assume role failed: {e}") from e
    creds = response.get("Credentials", {})
    access_key_id = str(creds.get("AccessKeyId", ""))
    secret_access_key = str(creds.get("SecretAccessKey", ""))
    session_token = str(creds.get("SessionToken", ""))
    if not access_key_id or not secret_access_key or not session_token:
        raise ValueError("assume role returned incomplete credentials")
    return AwsCredentials(access_key_id=access_key_id, secret_access_key=secret_access_key, session_token=session_token)


def resolve_credentials(
    *,
    auth_mode: str,
    access_key_id: str | None,
    secret_access_key: str | None,
    session_token: str | None,
    role_arn: str | None,
    role_external_id: str | None,
    role_session_name: str | None,
    region: str,
    simulate: bool = False,
) -> AwsCredentials:
    if simulate:
        return AwsCredentials(access_key_id="SIMULATED_ACCESS_KEY", secret_access_key="SIMULATED_SECRET_KEY", session_token=None)
    mode = auth_mode.upper()
    if mode != "ASSUME_ROLE":
        raise ValueError("only authMode=ASSUME_ROLE is supported")
    if not role_arn:
        raise ValueError("roleArn is required when authMode=ASSUME_ROLE")
    return _assume_role(
        role_arn=role_arn,
        role_session_name=role_session_name or f"stc-session-{int(time.time())}",
        region=region,
        external_id=role_external_id,
    )


def _assert_allowed_account(credentials: AwsCredentials, region: str) -> str:
    allowed = _allowed_account_ids()
    client = boto3.client(
        "sts",
        region_name=region,
        aws_access_key_id=credentials.access_key_id,
        aws_secret_access_key=credentials.secret_access_key,
        aws_session_token=credentials.session_token,
    )
    try:
        identity = client.get_caller_identity()
    except (BotoCoreError, ClientError) as e:
        raise ValueError(f"failed to verify caller identity: {e}") from e
    account_id = str(identity.get("Account", ""))
    if allowed and account_id not in allowed:
        raise ValueError(f"account not allowed: {account_id}")
    return account_id


def run_deploy(
    *,
    terraform_code: str,
    credentials: AwsCredentials,
    region: str,
    state_key: str,
    simulate: bool,
    on_progress: Callable[[str], None] | None = None,
) -> DeployExecutionResult:
    _guardrails_check(terraform_code, region)
    if simulate or os.getenv("DEPLOYMENT_SIMULATE_DEFAULT", "false").lower() == "true":
        return DeployExecutionResult(
            status="SUCCEEDED",
            log="[simulate] terraform apply skipped",
            resources={
                "status": "simulated",
                "region": region,
                "estimatedCount": _estimate_resource_count(terraform_code),
                **_build_state_metadata(work_dir=_session_work_dir(state_key), state_exists_before=False),
            },
        )

    account_id = _assert_allowed_account(credentials, region)
    terraform_bin = _resolve_terraform_bin()
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = credentials.access_key_id
    env["AWS_SECRET_ACCESS_KEY"] = credentials.secret_access_key
    env["AWS_DEFAULT_REGION"] = region
    if credentials.session_token:
        env["AWS_SESSION_TOKEN"] = credentials.session_token
    else:
        env.pop("AWS_SESSION_TOKEN", None)

    work, state_exists_before = _prepare_work_dir(terraform_code=terraform_code, state_key=state_key)

    rc_init, out_init = _run(
        [terraform_bin, "init", "-input=false", "-no-color"],
        cwd=work,
        env=env,
        timeout_sec=_terraform_init_timeout_sec(),
        on_output=on_progress,
    )
    if rc_init != 0:
        _cleanup_runtime_artifacts(work)
        return DeployExecutionResult(
            status="FAILED",
            log=f"[terraform init]\n{out_init}",
            resources=_build_state_metadata(work_dir=work, state_exists_before=state_exists_before),
        )

    rc_apply, out_apply = _run(
        [terraform_bin, "apply", "-auto-approve", "-input=false", "-no-color"],
        cwd=work,
        env=env,
        timeout_sec=_terraform_apply_timeout_sec(),
        on_output=on_progress,
    )
    if rc_apply != 0:
        _cleanup_runtime_artifacts(work)
        return DeployExecutionResult(
            status="FAILED",
            log=f"[terraform apply]\n{out_apply}",
            resources=_build_state_metadata(work_dir=work, state_exists_before=state_exists_before),
        )

    rc_output, out_output = _run([terraform_bin, "output", "-json"], cwd=work, env=env, timeout_sec=60, on_output=on_progress)
    _cleanup_runtime_artifacts(work)
    return DeployExecutionResult(
        status="SUCCEEDED",
        log=f"[terraform apply]\n{out_apply}",
        resources={
            "terraformOutputsRaw": out_output if rc_output == 0 and out_output.strip() else None,
            "accountId": account_id,
            "region": region,
            **_build_state_metadata(work_dir=work, state_exists_before=state_exists_before),
        },
    )


def run_destroy(
    *,
    terraform_code: str,
    credentials: AwsCredentials,
    region: str,
    state_key: str,
    simulate: bool,
    on_progress: Callable[[str], None] | None = None,
) -> DeployExecutionResult:
    _guardrails_check(terraform_code, region)
    if simulate or os.getenv("DEPLOYMENT_SIMULATE_DEFAULT", "false").lower() == "true":
        return DeployExecutionResult(
            status="SUCCEEDED",
            log="[simulate] terraform destroy skipped",
            resources={
                "status": "simulated-destroy",
                "region": region,
                **_build_state_metadata(work_dir=_session_work_dir(state_key), state_exists_before=False),
            },
        )

    account_id = _assert_allowed_account(credentials, region)
    terraform_bin = _resolve_terraform_bin()
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = credentials.access_key_id
    env["AWS_SECRET_ACCESS_KEY"] = credentials.secret_access_key
    env["AWS_DEFAULT_REGION"] = region
    if credentials.session_token:
        env["AWS_SESSION_TOKEN"] = credentials.session_token
    else:
        env.pop("AWS_SESSION_TOKEN", None)

    work, state_exists_before = _prepare_work_dir(terraform_code=terraform_code, state_key=state_key)
    if not (work / "terraform.tfstate").exists():
        return DeployExecutionResult(
            status="FAILED",
            log="[terraform destroy]\nno saved terraform state found for this session; deploy once successfully before destroy",
            resources=_build_state_metadata(work_dir=work, state_exists_before=state_exists_before),
        )

    rc_init, out_init = _run(
        [terraform_bin, "init", "-input=false", "-no-color"],
        cwd=work,
        env=env,
        timeout_sec=_terraform_init_timeout_sec(),
        on_output=on_progress,
    )
    if rc_init != 0:
        _cleanup_runtime_artifacts(work)
        return DeployExecutionResult(
            status="FAILED",
            log=f"[terraform init]\n{out_init}",
            resources=_build_state_metadata(work_dir=work, state_exists_before=state_exists_before),
        )

    rc_destroy, out_destroy = _run(
        [terraform_bin, "destroy", "-auto-approve", "-input=false", "-no-color"],
        cwd=work,
        env=env,
        timeout_sec=_terraform_destroy_timeout_sec(),
        on_output=on_progress,
    )
    if rc_destroy != 0:
        _cleanup_runtime_artifacts(work)
        return DeployExecutionResult(
            status="FAILED",
            log=f"[terraform destroy]\n{out_destroy}",
            resources=_build_state_metadata(work_dir=work, state_exists_before=state_exists_before),
        )

    _clear_saved_state(work)
    return DeployExecutionResult(
        status="SUCCEEDED",
        log=f"[terraform destroy]\n{out_destroy}",
        resources={
            "destroyed": True,
            "accountId": account_id,
            "region": region,
            **_build_state_metadata(work_dir=work, state_exists_before=state_exists_before, destroyed=True),
        },
    )
