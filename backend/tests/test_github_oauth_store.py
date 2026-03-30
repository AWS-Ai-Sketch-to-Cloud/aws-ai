from __future__ import annotations

from app.services.github_oauth_store import _decrypt_token, _encrypt_token


def test_encrypt_decrypt_roundtrip() -> None:
    token = "gho_example_token_123456"
    encrypted = _encrypt_token(token)
    decrypted = _decrypt_token(encrypted)
    assert decrypted == token


def test_decrypt_rejects_tampered_value() -> None:
    token = "gho_example_token_654321"
    encrypted = _encrypt_token(token)
    tampered = encrypted[:-2] + ("AA" if encrypted[-2:] != "AA" else "BB")
    assert _decrypt_token(tampered) is None
