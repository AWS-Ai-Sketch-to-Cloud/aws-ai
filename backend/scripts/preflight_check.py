from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_step(name: str, command: list[str], cwd: Path) -> tuple[bool, str]:
    printable = " ".join(shlex.quote(part) for part in command)
    print(f"[CHECK] {name}: {printable}")
    completed = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    if completed.stdout.strip():
        print(completed.stdout.rstrip())
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.rstrip())
        print(f"[FAIL] {name} (exit={completed.returncode})")
        return False, name
    print(f"[PASS] {name}")
    return True, name


def main() -> int:
    parser = argparse.ArgumentParser(description="Run backend preflight checks before release.")
    parser.add_argument("--min-score", type=float, default=0.75, help="Golden-set minimum average score")
    parser.add_argument("--run-real-eval", action="store_true", help="Run real repo eval dataset gate as well")
    parser.add_argument("--real-min-score", type=float, default=0.7, help="Real repo eval minimum average score")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip smoke_api_testclient")
    args = parser.parse_args()

    steps: list[tuple[str, list[str]]] = [
        ("security_baseline", [sys.executable, "scripts/security_baseline_check.py"]),
        (
            "golden_eval",
            [
                sys.executable,
                "scripts/eval_repo_analysis.py",
                "--dataset",
                "evals/golden_repo_analysis.json",
                "--min-score",
                str(args.min_score),
            ],
        ),
        ("cost_sanity", [sys.executable, "scripts/eval_cost_sanity.py"]),
        (
            "unit_tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_github_repo_analysis.py",
                "tests/test_github_oauth_store.py",
                "tests/test_github_status.py",
                "tests/test_ops_health.py",
                "tests/test_ops_feedback.py",
                "tests/test_security_middleware.py",
                "tests/test_exception_envelope.py",
            ],
        ),
    ]
    if args.run_real_eval:
        steps.append(
            (
                "real_repo_eval",
                [
                    sys.executable,
                    "scripts/eval_repo_analysis.py",
                    "--dataset",
                    "evals/real_repo_analysis.json",
                    "--min-score",
                    str(args.real_min_score),
                ],
            )
        )
    if not args.skip_smoke:
        steps.append(("smoke_api", [sys.executable, "scripts/smoke_api_testclient.py"]))

    for name, command in steps:
        ok, failed_name = _run_step(name, command, ROOT)
        if not ok:
            print(f"[SUMMARY] preflight failed at step: {failed_name}")
            return 1

    print("[SUMMARY] preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
