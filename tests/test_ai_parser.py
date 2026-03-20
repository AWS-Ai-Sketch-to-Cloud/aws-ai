from __future__ import annotations

import json
from pathlib import Path

from app.ai_parser import parse_architecture_with_retry


def load_schema() -> dict:
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "A_JSON_스키마_v1.json").read_text(encoding="utf-8"))


def test_local_parser_korean_input(monkeypatch) -> None:
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_FALLBACK_ENABLED", "true")
    schema = load_schema()

    out = parse_architecture_with_retry("서울 리전에 EC2 2개 mysql rds 퍼블릭", schema)
    assert out["region"] == "ap-northeast-2"
    assert out["ec2"]["count"] == 2
    assert out["rds"]["enabled"] is True
    assert out["rds"]["engine"] == "mysql"


def test_local_parser_ambiguous_public(monkeypatch) -> None:
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_FALLBACK_ENABLED", "true")
    schema = load_schema()

    out = parse_architecture_with_retry("퍼블릭으로 열어야 할지 모르겠어", schema)
    assert out["public"] is False

