from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

CONTRACT_VERSION = "v2"
ROOT = Path(__file__).resolve().parents[2]
ARCH_SCHEMA_PATH = ROOT / "A_JSON_스키마_v1.json"

with ARCH_SCHEMA_PATH.open("r", encoding="utf-8") as f:
    ARCH_SCHEMA = json.load(f)


def dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
