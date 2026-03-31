from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app


def _must(response, step: str) -> dict:
    if response.status_code >= 400:
        raise RuntimeError(f"{step} failed: {response.status_code} {response.text}")
    return response.json()


def _create_auth_headers(client: TestClient) -> dict[str, str]:
    suffix = int(time.time() * 1000)
    login_id = f"ghstatus{suffix}"
    email = f"ghstatus{suffix}@example.com"
    password = "TestPass!90"

    client_ip = f"10.1.0.{(suffix % 200) + 1}"
    request_headers = {"x-forwarded-for": client_ip}
    _must(
        client.post(
            "/api/auth/register",
            json={
                "loginId": login_id,
                "email": email,
                "password": password,
                "displayName": "GitHub Status User",
            },
            headers=request_headers,
        ),
        "register",
    )
    login = _must(
        client.post(
            "/api/auth/login",
            json={"loginId": login_id, "password": password},
            headers=request_headers,
        ),
        "login",
    )
    return {"Authorization": f"Bearer {login['accessToken']}"}


def test_github_status_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/github/status")
    assert response.status_code == 401


def test_github_status_without_token(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "test-id")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "test-secret")

    client = TestClient(app)
    headers = _create_auth_headers(client)
    response = client.get("/api/github/status", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["oauthConfigured"] is True
    assert body["tokenPresent"] is False
    assert body["tokenValid"] is False
    assert isinstance(body["issues"], list)
