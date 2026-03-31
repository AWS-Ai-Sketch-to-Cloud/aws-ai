from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "repo_analysis_failures.jsonl"
FEEDBACK_LOG_FILE = LOG_DIR / "repo_analysis_feedback.jsonl"


def log_repo_analysis_failure(payload: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **payload,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_recent_repo_analysis_failures(limit: int = 50) -> list[dict[str, Any]]:
    if not LOG_FILE.exists():
        return []
    rows: list[dict[str, Any]] = []
    with LOG_FILE.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[-limit:]:
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def summarize_repo_analysis_failures(limit: int = 50) -> dict[str, Any]:
    rows = read_recent_repo_analysis_failures(limit=limit)
    by_stage: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for row in rows:
        stage = str(row.get("stage") or "unknown")
        error_type = str(row.get("error_type") or "unknown")
        by_stage[stage] = by_stage.get(stage, 0) + 1
        by_type[error_type] = by_type.get(error_type, 0) + 1
    return {
        "total": len(rows),
        "byStage": by_stage,
        "byType": by_type,
        "recent": rows[-10:],
    }


def append_repo_analysis_feedback(payload: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **payload,
    }
    with FEEDBACK_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_latest_repo_analysis_feedback(*, user_id: str, full_name: str) -> dict[str, Any] | None:
    if not FEEDBACK_LOG_FILE.exists():
        return None
    latest: dict[str, Any] | None = None
    with FEEDBACK_LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if str(row.get("userId")) != user_id:
                continue
            if str(row.get("fullName")) != full_name:
                continue
            latest = row
    return latest
