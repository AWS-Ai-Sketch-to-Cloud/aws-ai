from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_http_exception_contains_request_id() -> None:
    client = TestClient(app)
    response = client.get("/api/github/repos")
    assert response.status_code == 401
    body = response.json()
    assert "detail" in body
    assert "requestId" in body


def test_validation_exception_contains_request_id() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/register", json={"loginId": ""})
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert "requestId" in body
