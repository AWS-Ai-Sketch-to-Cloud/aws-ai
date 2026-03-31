from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app


def _auth_client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(),
        login_id="ghstatus-test-user",
        email="ghstatus-test@example.com",
        display_name="GitHub Status User",
        role="USER",
    )
    return TestClient(app)


def test_github_status_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/github/status")
    assert response.status_code == 401


def test_github_status_without_token(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "test-id")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "test-secret")

    try:
        client = _auth_client()
        response = client.get("/api/github/status")
        assert response.status_code == 200
        body = response.json()
        assert body["oauthConfigured"] is True
        assert body["tokenPresent"] is False
        assert body["tokenValid"] is False
        assert isinstance(body["issues"], list)
    finally:
        app.dependency_overrides.clear()
