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
    login_id = f"test{suffix}"
    email = f"test{suffix}@example.com"
    password = "TestPass!90"

    _must(
        client.post(
            "/api/auth/register",
            json={
                "loginId": login_id,
                "email": email,
                "password": password,
                "displayName": "Test User",
            },
        ),
        "register",
    )
    login = _must(client.post("/api/auth/login", json={"loginId": login_id, "password": password}), "login")
    return {"Authorization": f"Bearer {login['accessToken']}"}


def test_analyze_requires_auth() -> None:
    client = TestClient(app)
    response = client.post(
        "/sessions/00000000-0000-0000-0000-000000000000/analyze",
        json={"input_text": "test", "input_type": "text"},
    )
    assert response.status_code == 401


def test_cost_contains_optimization_summary() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)

    project = _must(
        client.post("/api/projects", headers=headers, json={"name": "test-proj", "description": "test"}),
        "create project",
    )
    session = _must(
        client.post(
            f"/api/projects/{project['projectId']}/sessions",
            headers=headers,
            json={"inputType": "TEXT", "inputText": "baseline"},
        ),
        "create session",
    )
    session_id = session["sessionId"]

    _must(
        client.post(
            f"/api/sessions/{session_id}/architecture",
            headers=headers,
            json={
                "schemaVersion": "v1",
                "architectureJson": {
                    "vpc": True,
                    "ec2": {"count": 2, "instance_type": "t3.small"},
                    "rds": {"enabled": True, "engine": "mysql"},
                    "bedrock": {"enabled": True, "model": "anthropic.claude-3-haiku-20240307-v1:0"},
                    "additional_services": ["nat-gateway", "alb"],
                    "usage": {
                        "monthly_hours": 730,
                        "data_transfer_gb": 10,
                        "storage_gb": 30,
                        "requests_million": 0.5,
                    },
                    "public": True,
                    "region": "ap-northeast-2",
                },
            },
        ),
        "save architecture",
    )

    _must(client.post(f"/api/sessions/{session_id}/cost", headers=headers), "cost")
    detail = _must(client.get(f"/api/sessions/{session_id}", headers=headers), "detail")
    optimization = detail["cost"]["assumptionJson"].get("optimization")

    assert optimization is not None
    assert "cost_optimization" in optimization
    assert isinstance(optimization["cost_optimization"].get("savings_amount"), (int, float))
    scenarios = optimization.get("scenarios")
    assert isinstance(scenarios, list)
    assert len(scenarios) == 3
    assert optimization.get("recommended_scenario") in {"cost_saver", "balanced", "performance"}
