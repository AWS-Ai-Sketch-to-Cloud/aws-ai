from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = None
SessionLocal = None


def _load_database_url_from_env_file() -> None:
    if os.getenv("DATABASE_URL"):
        return

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if key == "DATABASE_URL" and value:
            os.environ["DATABASE_URL"] = value
            return


def _ensure_engine() -> None:
    global engine, SessionLocal
    if engine is not None and SessionLocal is not None:
        return

    _load_database_url_from_env_file()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Session:
    _ensure_engine()
    if SessionLocal is None:
        raise RuntimeError("database session factory is not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
