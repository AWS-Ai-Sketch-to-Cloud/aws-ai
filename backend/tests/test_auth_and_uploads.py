from __future__ import annotations

import time
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _must(response, step: str) -> dict:
    if response.status_code >= 400:
        raise RuntimeError(f"{step} failed: {response.status_code} {response.text}")
    return response.json()


def _create_auth_headers(client: TestClient) -> dict[str, str]:
    unique = uuid4().hex[:12]
    ip_headers = {"x-forwarded-for": f"198.51.{int(unique[:2], 16) % 250}.{int(unique[2:4], 16) % 250}"}
    login_id = f"upload{unique}"
    email = f"upload{unique}@example.com"
    password = "JwtPass!90"

    _must(
        client.post(
            "/api/auth/register",
            headers=ip_headers,
            json={
                "loginId": login_id,
                "email": email,
                "password": password,
                "displayName": "Upload User",
            },
        ),
        "register",
    )
    login = _must(
        client.post("/api/auth/login", headers=ip_headers, json={"loginId": login_id, "password": password}),
        "login",
    )
    return {"Authorization": f"Bearer {login['accessToken']}"}


def test_login_returns_jwt_and_me_accepts_it() -> None:
    client = TestClient(app)
    suffix = int(time.time() * 1000)
    ip_headers = {"x-forwarded-for": f"198.51.{suffix % 250}.{(suffix // 250) % 250}"}
    login_id = f"jwtfmt{suffix}"
    email = f"jwtfmt{suffix}@example.com"
    password = "JwtPass!90"

    _must(
        client.post(
            "/api/auth/register",
            headers=ip_headers,
            json={
                "loginId": login_id,
                "email": email,
                "password": password,
                "displayName": "JWT User",
            },
        ),
        "register",
    )
    login = _must(
        client.post("/api/auth/login", headers=ip_headers, json={"loginId": login_id, "password": password}),
        "login",
    )
    token = login["accessToken"]
    assert token.count(".") == 2
    assert not token.startswith("uid:")

    me = _must(client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"}), "me")
    assert me["loginId"] == login_id


def test_upload_image_and_fetch_uploaded_file() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)
    response = client.post(
        "/api/uploads/images",
        headers=headers,
        files={"file": ("diagram.png", b"\x89PNG\r\n\x1a\nmock", "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contentType"] == "image/png"
    assert body["url"].endswith(".png")

    fetched = client.get(body["url"].replace("http://127.0.0.1:8000", ""))
    assert fetched.status_code == 200
    assert fetched.content.startswith(b"\x89PNG")


def test_upload_rejects_non_image() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)
    response = client.post(
        "/api/uploads/images",
        headers=headers,
        files={"file": ("notes.txt", b"not-image", "text/plain")},
    )
    assert response.status_code == 422


def test_upload_requires_auth() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/uploads/images",
        files={"file": ("diagram.png", b"\x89PNG\r\n\x1a\nmock", "image/png")},
    )
    assert response.status_code == 401


def test_legacy_uid_token_is_rejected() -> None:
    client = TestClient(app)
    response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer uid:00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 401
