from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.env import load_env_file

engine = None
SessionLocal = None


def _ensure_engine() -> None:
    global engine, SessionLocal
    if engine is not None and SessionLocal is not None:
        return

    load_env_file()
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
