from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import HTTPException


def hash_text(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def to_access_token(user_id: UUID) -> str:
    return f"uid:{user_id}"


def user_id_from_auth_header(authorization: str | None) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith("uid:"):
        raise HTTPException(status_code=401, detail="invalid access token")
    raw_user_id = token.removeprefix("uid:")
    try:
        return UUID(raw_user_id)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="invalid access token") from e
