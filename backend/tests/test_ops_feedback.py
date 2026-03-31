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
    login_id = f"feedback{suffix}"
    email = f"feedback{suffix}@example.com"
    password = "TestPass!90"

    client_ip = f"10.3.0.{(suffix % 200) + 1}"
    request_headers = {"x-forwarded-for": client_ip}
    _must(
        client.post(
            "/api/auth/register",
            json={
                "loginId": login_id,
                "email": email,
                "password": password,
                "displayName": "Feedback User",
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


def test_repo_analysis_feedback_roundtrip() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)
    full_name = "example/repo"

    save_res = client.post(
        "/api/ops/repo-analysis-feedback",
        headers=headers,
        json={"fullName": full_name, "verdict": "APPROVE", "note": "배포 진행 가능"},
    )
    assert save_res.status_code == 200
    saved = save_res.json()
    assert saved["saved"] is True
    assert saved["verdict"] == "APPROVE"

    get_res = client.get(
        f"/api/ops/repo-analysis-feedback?fullName={full_name}",
        headers=headers,
    )
    assert get_res.status_code == 200
    body = get_res.json()
    assert body["fullName"] == full_name
    assert body["feedback"] is not None
    assert body["feedback"]["verdict"] == "APPROVE"
