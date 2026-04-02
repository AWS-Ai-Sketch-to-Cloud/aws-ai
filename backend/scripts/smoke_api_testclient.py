from __future__ import annotations

import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app


def _must(response, step: str) -> dict:
    if response.status_code >= 400:
        raise RuntimeError(f"{step} failed: {response.status_code} {response.text}")
    return response.json()


def run_smoke() -> None:
    client = TestClient(app)
    suffix = int(time.time())
    login_id = f"smoke{suffix}"
    email = f"smoke{suffix}@example.com"
    password = "SmokePass!90"

    _must(
        client.post(
            "/api/auth/register",
            json={
                "loginId": login_id,
                "email": email,
                "password": password,
                "displayName": "Smoke User",
            },
        ),
        "register",
    )
    login = _must(client.post("/api/auth/login", json={"loginId": login_id, "password": password}), "login")
    auth_headers = {"Authorization": f"Bearer {login['accessToken']}"}

    project = _must(
        client.post("/api/projects", headers=auth_headers, json={"name": f"smoke-{suffix}", "description": "smoke"}),
        "create project",
    )
    project_id = project["projectId"]
    session = _must(
        client.post(
            f"/api/projects/{project_id}/sessions",
            headers=auth_headers,
            json={"inputType": "TEXT", "inputText": "baseline"},
        ),
        "create session",
    )
    session_id = session["sessionId"]

    analyze = _must(
        client.post(
            f"/api/sessions/{session_id}/analyze",
            headers=auth_headers,
            json={
                "inputText": (
                    "Seoul, public architecture with 2 EC2 t3.small, RDS mysql, NAT gateway and ALB. "
                    "data transfer 10GB, storage 30GB, requests 0.5 million"
                ),
                "inputType": "text",
            },
        ),
        "analyze",
    )
    if analyze.get("status") != "generated":
        raise RuntimeError(f"analyze status is not generated: {analyze}")

    _must(client.post(f"/api/sessions/{session_id}/terraform", headers=auth_headers), "terraform")
    _must(client.post(f"/api/sessions/{session_id}/cost", headers=auth_headers), "cost")
    detail = _must(client.get(f"/api/sessions/{session_id}", headers=auth_headers), "detail")

    cost = detail.get("cost")
    if not cost:
        raise RuntimeError("missing cost in detail response")
    assumptions = cost.get("assumptionJson", {})
    optimization = assumptions.get("optimization", {})
    if "cost_optimization" not in optimization:
        raise RuntimeError("missing optimization.cost_optimization")
    scenarios = optimization.get("scenarios", [])
    if not isinstance(scenarios, list) or len(scenarios) < 3:
        raise RuntimeError("missing optimization scenarios")

    print(
        "SMOKE_OK",
        {
            "sessionId": session_id,
            "status": detail.get("status"),
            "currency": cost.get("currency"),
            "monthlyTotal": cost.get("monthlyTotal"),
            "pricingSource": assumptions.get("pricing_source"),
            "savings": optimization.get("cost_optimization", {}).get("savings_amount"),
            "scenarioCount": len(scenarios),
            "recommendedScenario": optimization.get("recommended_scenario"),
        },
    )


if __name__ == "__main__":
    run_smoke()
