from __future__ import annotations

import os
from pathlib import Path


def load_env_file() -> None:
    # Support both backend/.env and repo-root .env for local runs.
    base_dir = Path(__file__).resolve()
    candidate_paths = [
        base_dir.parents[2] / ".env",
        base_dir.parents[3] / ".env",
    ]

    for env_path in candidate_paths:
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
