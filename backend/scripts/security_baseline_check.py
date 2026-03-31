from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.env import load_env_file


def _bool(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() == "true"


def main() -> int:
    load_env_file()
    errors: list[str] = []
    warnings: list[str] = []

    token_key = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY", "").strip()
    if not token_key or token_key == "change-this-to-a-long-random-secret":
        errors.append("GITHUB_TOKEN_ENCRYPTION_KEY가 기본값이거나 비어 있습니다.")
    elif len(token_key) < 32:
        warnings.append("GITHUB_TOKEN_ENCRYPTION_KEY 길이가 짧습니다(권장 32자 이상).")

    if _bool("GITHUB_REPO_ANALYSIS_AI_ONLY", "true"):
        if not _bool("BEDROCK_ENABLED", "true"):
            errors.append("AI 전용 모드인데 BEDROCK_ENABLED=false 입니다.")
        if not _bool("BEDROCK_STRICT_MODE", "false"):
            errors.append("AI 전용 모드인데 BEDROCK_STRICT_MODE=true가 아닙니다.")
        if _bool("BEDROCK_FALLBACK_ENABLED", "true"):
            errors.append("AI 전용 모드인데 BEDROCK_FALLBACK_ENABLED=false가 아닙니다.")

    auth_limit = int(os.getenv("AUTH_RATE_LIMIT", "20"))
    auth_window = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"))
    if auth_limit <= 0 or auth_window <= 0:
        errors.append("AUTH_RATE_LIMIT/AUTH_RATE_LIMIT_WINDOW_SECONDS는 양수여야 합니다.")

    if warnings:
        print("[WARN] security baseline warnings:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("[FAIL] security baseline:")
        for error in errors:
            print(f"- {error}")
        return 2

    print("[PASS] security baseline check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
