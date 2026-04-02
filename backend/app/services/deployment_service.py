from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
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
    path_bin = shutil.which("terraform")
    if path_bin:
        return path_bin
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


def _estimate_resource_count(terraform_code: str) -> int:
    return terraform_code.count('resource "')


def _guardrails_check(terraform_code: str, region: str) -> None:
    if region not in _allowed_regions():
        raise ValueError(f"region not allowed: {region}")
    count = _estimate_resource_count(terraform_code)
    if count > _max_resource_count():
        raise ValueError(f"resource count limit exceeded: {count}>{_max_resource_count()}")


def _run(cmd: list[str], cwd: Path, env: dict[str, str], timeout_sec: int = 300) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output.strip()


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
    simulate: bool,
) -> DeployExecutionResult:
    _guardrails_check(terraform_code, region)
    if simulate or os.getenv("DEPLOYMENT_SIMULATE_DEFAULT", "false").lower() == "true":
        return DeployExecutionResult(
            status="SUCCEEDED",
            log="[simulate] terraform apply skipped",
            resources={"status": "simulated", "region": region, "estimatedCount": _estimate_resource_count(terraform_code)},
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

    with tempfile.TemporaryDirectory(prefix="stc-deploy-") as temp_dir:
        work = Path(temp_dir)
        (work / "main.tf").write_text(terraform_code, encoding="utf-8")

        rc_init, out_init = _run([terraform_bin, "init", "-input=false", "-no-color"], cwd=work, env=env)
        if rc_init != 0:
            return DeployExecutionResult(status="FAILED", log=f"[terraform init]\n{out_init}")

        rc_apply, out_apply = _run(
            [terraform_bin, "apply", "-auto-approve", "-input=false", "-no-color"],
            cwd=work,
            env=env,
            timeout_sec=900,
        )
        if rc_apply != 0:
            return DeployExecutionResult(status="FAILED", log=f"[terraform apply]\n{out_apply}")

        rc_output, out_output = _run([terraform_bin, "output", "-json"], cwd=work, env=env, timeout_sec=60)
        return DeployExecutionResult(
            status="SUCCEEDED",
            log=f"[terraform apply]\n{out_apply}",
            resources={
                "terraformOutputsRaw": out_output if rc_output == 0 and out_output.strip() else None,
                "accountId": account_id,
                "region": region,
            },
        )


def run_destroy(
    *,
    terraform_code: str,
    credentials: AwsCredentials,
    region: str,
    simulate: bool,
) -> DeployExecutionResult:
    _guardrails_check(terraform_code, region)
    if simulate or os.getenv("DEPLOYMENT_SIMULATE_DEFAULT", "false").lower() == "true":
        return DeployExecutionResult(
            status="SUCCEEDED",
            log="[simulate] terraform destroy skipped",
            resources={"status": "simulated-destroy", "region": region},
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

    with tempfile.TemporaryDirectory(prefix="stc-destroy-") as temp_dir:
        work = Path(temp_dir)
        (work / "main.tf").write_text(terraform_code, encoding="utf-8")

        rc_init, out_init = _run([terraform_bin, "init", "-input=false", "-no-color"], cwd=work, env=env)
        if rc_init != 0:
            return DeployExecutionResult(status="FAILED", log=f"[terraform init]\n{out_init}")

        rc_destroy, out_destroy = _run(
            [terraform_bin, "destroy", "-auto-approve", "-input=false", "-no-color"],
            cwd=work,
            env=env,
            timeout_sec=900,
        )
        if rc_destroy != 0:
            return DeployExecutionResult(status="FAILED", log=f"[terraform destroy]\n{out_destroy}")

        return DeployExecutionResult(
            status="SUCCEEDED",
            log=f"[terraform destroy]\n{out_destroy}",
            resources={"destroyed": True, "accountId": account_id, "region": region},
        )
