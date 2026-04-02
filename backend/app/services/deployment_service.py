from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeployExecutionResult:
    status: str
    log: str
    resources: dict[str, object] | None = None


def _resolve_terraform_bin() -> str:
    path_bin = shutil.which("terraform")
    if path_bin:
        return path_bin
    return "terraform"


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


def run_deploy(
    *,
    terraform_code: str,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None,
    region: str,
    simulate: bool,
) -> DeployExecutionResult:
    if simulate or os.getenv("DEPLOYMENT_SIMULATE_DEFAULT", "false").lower() == "true":
        return DeployExecutionResult(
            status="SUCCEEDED",
            log="[simulate] terraform apply skipped",
            resources={"status": "simulated", "region": region, "estimatedCount": 5},
        )

    terraform_bin = _resolve_terraform_bin()
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = access_key_id
    env["AWS_SECRET_ACCESS_KEY"] = secret_access_key
    env["AWS_DEFAULT_REGION"] = region
    if session_token:
        env["AWS_SESSION_TOKEN"] = session_token
    else:
        env.pop("AWS_SESSION_TOKEN", None)

    with tempfile.TemporaryDirectory(prefix="stc-deploy-") as temp_dir:
        work = Path(temp_dir)
        (work / "main.tf").write_text(terraform_code, encoding="utf-8")

        rc_init, out_init = _run(
            [terraform_bin, "init", "-input=false", "-no-color"],
            cwd=work,
            env=env,
        )
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
        if rc_output == 0 and out_output.strip():
            resources = {"terraformOutputsRaw": out_output}
        else:
            resources = {"terraformOutputsRaw": None}

        return DeployExecutionResult(status="SUCCEEDED", log=f"[terraform apply]\n{out_apply}", resources=resources)


def run_destroy(
    *,
    terraform_code: str,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None,
    region: str,
    simulate: bool,
) -> DeployExecutionResult:
    if simulate or os.getenv("DEPLOYMENT_SIMULATE_DEFAULT", "false").lower() == "true":
        return DeployExecutionResult(
            status="SUCCEEDED",
            log="[simulate] terraform destroy skipped",
            resources={"status": "simulated-destroy", "region": region},
        )

    terraform_bin = _resolve_terraform_bin()
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = access_key_id
    env["AWS_SECRET_ACCESS_KEY"] = secret_access_key
    env["AWS_DEFAULT_REGION"] = region
    if session_token:
        env["AWS_SESSION_TOKEN"] = session_token
    else:
        env.pop("AWS_SESSION_TOKEN", None)

    with tempfile.TemporaryDirectory(prefix="stc-destroy-") as temp_dir:
        work = Path(temp_dir)
        (work / "main.tf").write_text(terraform_code, encoding="utf-8")

        rc_init, out_init = _run(
            [terraform_bin, "init", "-input=false", "-no-color"],
            cwd=work,
            env=env,
        )
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
            resources={"destroyed": True, "region": region},
        )
