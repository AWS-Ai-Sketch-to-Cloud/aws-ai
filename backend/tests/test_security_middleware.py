from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_root_has_security_headers_and_request_id() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("x-request-id")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_auth_rate_limit_applies() -> None:
    client = TestClient(app)
    blocked = False
    for _ in range(35):
        response = client.post(
            "/api/auth/login",
            json={"loginId": "not-exist-user", "password": "wrong-password"},
        )
        if response.status_code == 429:
            blocked = True
            break
    assert blocked
