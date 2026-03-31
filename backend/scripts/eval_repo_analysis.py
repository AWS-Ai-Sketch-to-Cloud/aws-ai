from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai_parser import parse_architecture_with_retry
from app.core.constants import ARCH_SCHEMA
from app.core.env import load_env_file
from app.routers.github import (
    _apply_repo_sanity_overrides,
    _detect_flags,
    _normalize_recommended_stack,
)
from app.services.github_ai_report import generate_repo_report_with_ai


def _contains_hangul(text: str) -> bool:
    return any(0xAC00 <= ord(ch) <= 0xD7A3 for ch in text)


def _normalize_text_list(values: list[Any]) -> list[str]:
    return [str(v).strip() for v in values if str(v).strip()]


def _extract_files_from_prompt(repo_prompt: str) -> list[str]:
    lines = repo_prompt.splitlines()
    files: list[str] = []
    in_tree = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("file tree sample:"):
            in_tree = True
            continue
        if in_tree and stripped.lower().startswith("important file snippets:"):
            break
        if in_tree and stripped.startswith("- "):
            files.append(stripped[2:].strip())
    return files


def _extract_file_contents_from_prompt(repo_prompt: str) -> dict[str, str]:
    contents: dict[str, str] = {}
    lines = repo_prompt.splitlines()
    current_file: str | None = None
    buffer: list[str] = []
    for line in lines:
        marker = re.match(r"^\[(.+?)\]\s*$", line.strip())
        if marker:
            if current_file is not None:
                contents[current_file.lower()] = "\n".join(buffer).strip()
            current_file = marker.group(1).strip()
            buffer = []
            continue
        if current_file is not None:
            buffer.append(line)
    if current_file is not None:
        contents[current_file.lower()] = "\n".join(buffer).strip()
    return contents


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected", {}) or {}
    repo_prompt = str(case.get("repo_prompt", "")).strip()
    if not repo_prompt:
        return {
            "id": case.get("id", "unknown"),
            "score": 0.0,
            "passed": False,
            "checks": 1,
            "passed_checks": 0,
            "failures": ["repo_prompt is empty"],
        }

    files = _extract_files_from_prompt(repo_prompt)
    file_contents = _extract_file_contents_from_prompt(repo_prompt)
    architecture, analysis_meta = parse_architecture_with_retry(repo_prompt, ARCH_SCHEMA)
    detected = _detect_flags(files)
    architecture = _apply_repo_sanity_overrides(
        architecture=architecture,
        detected=detected,
        file_contents=file_contents,
    )
    report, _ = generate_repo_report_with_ai(
        repo_prompt=repo_prompt,
        architecture=architecture,
        model_rationale=analysis_meta.get("rationale") if isinstance(analysis_meta, dict) else None,
    )

    recommended = _normalize_recommended_stack(
        raw_stack=_normalize_text_list(report.get("recommendedStack", [])),
        detected=detected,
        architecture=architecture,
        files=files,
    )
    additional = {str(s).lower() for s in architecture.get("additional_services", []) if str(s).strip()}

    total_checks = 0
    passed_checks = 0
    failures: list[str] = []

    recommended_any = _normalize_text_list(expected.get("recommended_any", []))
    if recommended_any:
        total_checks += 1
        if any(item in recommended for item in recommended_any):
            passed_checks += 1
        else:
            failures.append(f"recommended_any failed: expected one of {recommended_any}, got {recommended}")

    forbidden_all = _normalize_text_list(expected.get("forbidden_all", []))
    if forbidden_all:
        total_checks += 1
        present = [item for item in forbidden_all if item in recommended]
        if not present:
            passed_checks += 1
        else:
            failures.append(f"forbidden_all failed: found forbidden stack items {present}")

    if "ec2_max" in expected:
        total_checks += 1
        ec2_count = int((architecture.get("ec2", {}) or {}).get("count", 1))
        ec2_max = int(expected["ec2_max"])
        if ec2_count <= ec2_max:
            passed_checks += 1
        else:
            failures.append(f"ec2_max failed: ec2_count={ec2_count}, expected<={ec2_max}")

    if "rds_enabled" in expected:
        total_checks += 1
        rds_enabled = bool((architecture.get("rds", {}) or {}).get("enabled", False))
        if rds_enabled == bool(expected["rds_enabled"]):
            passed_checks += 1
        else:
            failures.append(
                f"rds_enabled failed: rds_enabled={rds_enabled}, expected={bool(expected['rds_enabled'])}"
            )

    architecture_services_any = _normalize_text_list(expected.get("architecture_services_any", []))
    if architecture_services_any:
        total_checks += 1
        if any(service.lower() in additional for service in architecture_services_any):
            passed_checks += 1
        else:
            failures.append(
                f"architecture_services_any failed: expected one of {architecture_services_any}, got {sorted(additional)}"
            )

    if bool(expected.get("must_be_korean", False)):
        total_checks += 1
        summary = str(report.get("summary", ""))
        findings = " ".join(_normalize_text_list(report.get("findings", [])))
        steps = " ".join(_normalize_text_list(report.get("deploymentSteps", [])))
        if _contains_hangul(summary) and (_contains_hangul(findings) or _contains_hangul(steps)):
            passed_checks += 1
        else:
            failures.append("must_be_korean failed: report text has insufficient Hangul content")

    if total_checks == 0:
        total_checks = 1
        passed_checks = 1

    score = round(passed_checks / total_checks, 3)
    return {
        "id": case.get("id", "unknown"),
        "score": score,
        "passed": passed_checks == total_checks,
        "checks": total_checks,
        "passed_checks": passed_checks,
        "failures": failures,
        "recommended": recommended,
        "architecture": architecture,
    }


def run_evaluation(dataset_path: Path, min_score: float) -> int:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not isinstance(cases, list) or not cases:
        print("No evaluation cases found.")
        return 1

    results = [_score_case(case) for case in cases if isinstance(case, dict)]
    if not results:
        print("No valid cases to evaluate.")
        return 1

    avg_score = round(sum(result["score"] for result in results) / len(results), 3)
    pass_count = sum(1 for result in results if result["passed"])
    print(f"[EVAL] cases={len(results)} passed={pass_count} avg_score={avg_score} min_score={min_score}")

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"- {status} {result['id']} score={result['score']} ({result['passed_checks']}/{result['checks']})")
        if result["failures"]:
            for failure in result["failures"]:
                print(f"  * {failure}")

    return 0 if avg_score >= min_score else 2


def main() -> int:
    load_env_file()

    parser = argparse.ArgumentParser(description="Evaluate repository AI analysis against golden set.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "evals" / "golden_repo_analysis.json",
        help="Path to golden dataset JSON",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.75,
        help="Fail process if average score is below this threshold",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}")
        return 1
    return run_evaluation(args.dataset, args.min_score)


if __name__ == "__main__":
    raise SystemExit(main())
