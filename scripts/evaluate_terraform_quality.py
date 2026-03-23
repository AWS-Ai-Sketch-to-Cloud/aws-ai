from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai_parser import parse_architecture_with_retry
from app.terraform_generator import generate_terraform_from_architecture
from scripts.evaluate_inputs import DEFAULT_TESTSET_PATHS, load_cases_from_files


def load_schema() -> dict[str, Any]:
    return json.loads((ROOT / "A_JSON_스키마_v1.json").read_text(encoding="utf-8"))


def run_cmd(cmd: list[str], cwd: Path, timeout_sec: int = 120) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, out.strip()


def main() -> None:
    schema = load_schema()
    cases = load_cases_from_files(DEFAULT_TESTSET_PATHS)
    if not cases:
        raise RuntimeError("no test cases found")

    terraform_bin = os.getenv("TERRAFORM_BIN", "terraform")
    passed = 0
    failed = 0
    reasons: dict[str, int] = {}

    with tempfile.TemporaryDirectory(prefix="tf_eval_") as temp_dir:
        work = Path(temp_dir)
        # Init once, reuse provider/plugin cache for all cases.
        (work / "main.tf").write_text(
            """
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
provider "aws" { region = "ap-northeast-2" }
            """.strip()
            + "\n",
            encoding="utf-8",
        )
        init_code, init_out = run_cmd(
            [terraform_bin, "init", "-backend=false", "-input=false", "-no-color"],
            cwd=work,
            timeout_sec=300,
        )
        if init_code != 0:
            print("=== Terraform Quality Evaluation ===")
            print("total: 0")
            print("passed: 0")
            print("failed: 0")
            print("pass_ratio: 0.0%")
            reason = "terraform_not_found" if "not found" in init_out.lower() else "init_failed"
            print("reasons:", {reason: 1})
            print("init_output:", init_out[:500])
            return

        for case in cases:
            arch = parse_architecture_with_retry(case["input"], schema)
            tf = generate_terraform_from_architecture(arch)
            (work / "main.tf").write_text(tf, encoding="utf-8")
            v_code, v_out = run_cmd([terraform_bin, "validate", "-no-color"], cwd=work, timeout_sec=120)
            if v_code == 0:
                passed += 1
            else:
                failed += 1
                key = "validate_failed"
                if "not found" in v_out.lower():
                    key = "terraform_not_found"
                elif "timed out" in v_out.lower():
                    key = "validate_timeout"
                reasons[key] = reasons.get(key, 0) + 1

    total = len(cases)
    ratio = (passed / total) * 100 if total else 0
    print("=== Terraform Quality Evaluation ===")
    print(f"total: {total}")
    print(f"passed: {passed}")
    print(f"failed: {failed}")
    print(f"pass_ratio: {ratio:.1f}%")
    print("reasons:", reasons if reasons else "{}")


if __name__ == "__main__":
    main()

