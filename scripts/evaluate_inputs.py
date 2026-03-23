from __future__ import annotations

import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai_parser import AIParseError, parse_architecture_with_retry

SCHEMA_PATH = ROOT / "A_JSON_스키마_v1.json"
DEFAULT_TESTSET_PATHS = [
    ROOT / "A_입력테스트셋_v1.md",
    ROOT / "A_입력테스트셋_v2.md",
]


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def parse_testset(markdown: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"- input: `(?P<input>.*?)`\s+- expected:\s+```json\s+(?P<json>\{.*?\})\s+```",
        re.DOTALL,
    )
    cases: list[dict[str, Any]] = []
    for idx, match in enumerate(pattern.finditer(markdown), start=1):
        raw_input = match.group("input").strip()
        expected_raw = match.group("json").strip()
        expected = json.loads(expected_raw)
        cases.append({"id": idx, "input": raw_input, "expected": expected})
    return cases


def load_cases_from_files(paths: list[Path]) -> list[dict[str, Any]]:
    all_cases: list[dict[str, Any]] = []
    running_id = 1
    for path in paths:
        if not path.exists():
            continue
        markdown = path.read_text(encoding="utf-8")
        cases = parse_testset(markdown)
        for case in cases:
            case["id"] = running_id
            case["source"] = path.name
            running_id += 1
            all_cases.append(case)
    return all_cases


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> tuple[bool, list[str]]:
    diffs: list[str] = []
    keys = sorted(set(expected.keys()) | set(actual.keys()))
    for key in keys:
        if expected.get(key) != actual.get(key):
            diffs.append(f"{key}: expected={expected.get(key)!r}, actual={actual.get(key)!r}")
    return (len(diffs) == 0, diffs)


def main() -> None:
    schema = load_schema()
    cases = load_cases_from_files(DEFAULT_TESTSET_PATHS)
    if not cases:
        raise RuntimeError("no test cases parsed from input testset files")

    success = 0
    failed_cases: list[dict[str, Any]] = []
    error_stats: dict[str, int] = {}

    for case in cases:
        try:
            actual = parse_architecture_with_retry(case["input"], schema)
            ok, diffs = compare(case["expected"], actual)
            if ok:
                success += 1
            else:
                failed_cases.append(
                    {
                        "id": case["id"],
                        "source": case.get("source"),
                        "input": case["input"],
                        "reason": "MISMATCH",
                        "diffs": diffs,
                        "actual": actual,
                    }
                )
                error_stats["MISMATCH"] = error_stats.get("MISMATCH", 0) + 1
        except AIParseError as e:
            failed_cases.append(
                {
                    "id": case["id"],
                    "source": case.get("source"),
                    "input": case["input"],
                    "reason": e.code,
                    "message": e.message,
                }
            )
            error_stats[e.code] = error_stats.get(e.code, 0) + 1

    total = len(cases)
    accuracy = (success / total) * 100

    print("=== A Parser Evaluation ===")
    print("sources:", ", ".join(p.name for p in DEFAULT_TESTSET_PATHS if p.exists()))
    print(f"total: {total}")
    print(f"success: {success}")
    print(f"failed: {total - success}")
    print(f"accuracy: {accuracy:.1f}%")
    print()
    print("error_stats:", error_stats if error_stats else "{}")
    print()

    if failed_cases:
        print("=== Failed Cases ===")
        for case in failed_cases:
            print(f"[#{case['id']}] {case['reason']}")
            if case.get("source"):
                print(f"source: {case['source']}")
            print(f"input: {case['input']}")
            if "message" in case:
                print(f"message: {case['message']}")
            if "diffs" in case:
                for diff in case["diffs"]:
                    print(f" - {diff}")
                print(f"actual: {json.dumps(case['actual'], ensure_ascii=False)}")
            print()


if __name__ == "__main__":
    main()
