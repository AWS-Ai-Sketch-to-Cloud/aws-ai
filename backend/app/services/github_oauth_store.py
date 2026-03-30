from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GitHubOAuthToken

_TOKEN_TTL = timedelta(days=30)
_NONCE_SIZE = 16
_BLOCK_SIZE = 32


def _derive_master_key() -> bytes:
    seed = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY") or os.getenv("DATABASE_URL") or "local-dev-key"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _xor_stream(plaintext: bytes, *, key: bytes, nonce: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(plaintext):
        block = hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
        output.extend(block)
        counter += 1
    return bytes(p ^ k for p, k in zip(plaintext, output[: len(plaintext)], strict=False))


def _encrypt_token(token: str) -> str:
    key = _derive_master_key()
    enc_key = hashlib.sha256(key + b"enc").digest()
    mac_key = hashlib.sha256(key + b"mac").digest()

    nonce = secrets.token_bytes(_NONCE_SIZE)
    plaintext = token.encode("utf-8")
    ciphertext = _xor_stream(plaintext, key=enc_key, nonce=nonce)
    mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    blob = nonce + mac + ciphertext
    return base64.urlsafe_b64encode(blob).decode("utf-8")


def _decrypt_token(encrypted: str) -> str | None:
    key = _derive_master_key()
    enc_key = hashlib.sha256(key + b"enc").digest()
    mac_key = hashlib.sha256(key + b"mac").digest()

    try:
        blob = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
    except Exception:
        return None

    if len(blob) <= _NONCE_SIZE + _BLOCK_SIZE:
        return None

    nonce = blob[:_NONCE_SIZE]
    mac = blob[_NONCE_SIZE : _NONCE_SIZE + _BLOCK_SIZE]
    ciphertext = blob[_NONCE_SIZE + _BLOCK_SIZE :]
    expected_mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        return None

    plaintext = _xor_stream(ciphertext, key=enc_key, nonce=nonce)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError:
        return None


def put_github_access_token(db: Session, user_id: UUID | str, access_token: str) -> None:
    parsed_user_id = UUID(str(user_id))
    encrypted = _encrypt_token(access_token)
    now = datetime.now(timezone.utc)

    token_row = db.scalars(
        select(GitHubOAuthToken).where(GitHubOAuthToken.user_id == parsed_user_id).limit(1)
    ).first()
    if token_row:
        token_row.encrypted_access_token = encrypted
        token_row.updated_at = now
    else:
        db.add(
            GitHubOAuthToken(
                user_id=parsed_user_id,
                encrypted_access_token=encrypted,
                updated_at=now,
            )
        )
    db.flush()


def get_github_access_token(db: Session, user_id: UUID | str) -> str | None:
    parsed_user_id = UUID(str(user_id))
    token_row = db.scalars(
        select(GitHubOAuthToken).where(GitHubOAuthToken.user_id == parsed_user_id).limit(1)
    ).first()
    if token_row is None:
        return None

    now = datetime.now(timezone.utc)
    last_seen = token_row.updated_at or token_row.created_at
    if last_seen is not None:
        seen_utc = last_seen if last_seen.tzinfo else last_seen.replace(tzinfo=timezone.utc)
        if seen_utc + _TOKEN_TTL <= now:
            db.delete(token_row)
            db.flush()
            return None

    access_token = _decrypt_token(token_row.encrypted_access_token)
    if access_token is None:
        return None
    return access_token
