from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from uuid import UUID

from fastapi import HTTPException


def hash_text(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET_KEY", "dev-insecure-jwt-secret-change-me")


def _jwt_issuer() -> str:
    return os.getenv("JWT_ISSUER", "sketch-to-cloud")


def _access_token_ttl_seconds() -> int:
    try:
        return max(60, int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "3600")))
    except ValueError:
        return 3600


def to_access_token(user_id: UUID) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + _access_token_ttl_seconds(),
        "iss": _jwt_issuer(),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(_jwt_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def _parse_jwt_access_token(token: str) -> UUID:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as e:
        raise HTTPException(status_code=401, detail="invalid access token") from e

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = hmac.new(_jwt_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_signature = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(status_code=401, detail="invalid access token")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="invalid access token") from e

    if payload.get("iss") != _jwt_issuer():
        raise HTTPException(status_code=401, detail="invalid access token")

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= int(time.time()):
        raise HTTPException(status_code=401, detail="access token expired")

    raw_sub = payload.get("sub")
    if not isinstance(raw_sub, str):
        raise HTTPException(status_code=401, detail="invalid access token")
    try:
        return UUID(raw_sub)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="invalid access token") from e


def user_id_from_auth_header(authorization: str | None) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return _parse_jwt_access_token(token)
