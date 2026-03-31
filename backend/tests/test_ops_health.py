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
    login_id = f"ops{suffix}"
    email = f"ops{suffix}@example.com"
    password = "TestPass!90"

    client_ip = f"10.2.0.{(suffix % 200) + 1}"
    request_headers = {"x-forwarded-for": client_ip}
    _must(
        client.post(
            "/api/auth/register",
            json={
                "loginId": login_id,
                "email": email,
                "password": password,
                "displayName": "Ops User",
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


def test_repo_analysis_health_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/ops/repo-analysis-health")
    assert response.status_code == 401


def test_repo_analysis_health_shape() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)
    response = client.get("/api/ops/repo-analysis-health", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "policy" in body
    assert "cache" in body
    assert "failures" in body
    assert "recommendations" in body


def test_repo_analysis_readiness_shape() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)
    response = client.get("/api/ops/readiness", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "score" in body
    assert "grade" in body
    assert "checklist" in body
