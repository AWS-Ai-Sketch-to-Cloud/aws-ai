from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def _run(cmd: list[str], cwd: Path, timeout_sec: int = 60) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output.strip()


def validate_terraform_code(terraform_code: str) -> tuple[str, str]:
    try:
        with tempfile.TemporaryDirectory(prefix="tf_validate_") as temp_dir:
            work = Path(temp_dir)
            (work / "main.tf").write_text(terraform_code, encoding="utf-8")

            init_code, init_output = _run(
                ["terraform", "init", "-backend=false", "-input=false", "-no-color"],
                cwd=work,
            )
            if init_code != 0:
                return "FAILED", f"[terraform init]\n{init_output}"

            validate_code, validate_output = _run(
                ["terraform", "validate", "-no-color"],
                cwd=work,
            )
            if validate_code != 0:
                return "FAILED", f"[terraform validate]\n{validate_output}"

            return "PASSED", f"[terraform validate]\n{validate_output}"
    except FileNotFoundError:
        return "FAILED", "terraform command not found. Install Terraform and ensure it is in PATH."
    except subprocess.TimeoutExpired:
        return "FAILED", "terraform validation timed out."
    except Exception as e:  # noqa: BLE001
        return "FAILED", str(e)

