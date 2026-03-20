from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_full_pipeline_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not set")

    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_FALLBACK_ENABLED", "true")

    client = TestClient(app)

    project_resp = client.post("/api/projects", json={"name": "integration-flow", "description": "pytest flow"})
    assert project_resp.status_code == 200
    project_id = project_resp.json()["projectId"]

    session_resp = client.post(
        f"/api/projects/{project_id}/sessions",
        json={"inputType": "TEXT", "inputText": "서울 리전에 EC2 2개 mysql rds 퍼블릭"},
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["sessionId"]

    analyze_resp = client.post(
        f"/sessions/{session_id}/analyze",
        json={"input_text": "서울 리전에 EC2 2개 mysql rds 퍼블릭"},
    )
    assert analyze_resp.status_code == 200
    assert analyze_resp.json()["status"] == "generated"

    tf_resp = client.post(f"/api/sessions/{session_id}/terraform")
    assert tf_resp.status_code == 200
    assert tf_resp.json()["status"] == "GENERATED"
    assert "terraform {" in tf_resp.json()["terraformCode"]
    assert tf_resp.json()["validationStatus"] in ("PASSED", "FAILED")

    cost_resp = client.post(f"/api/sessions/{session_id}/cost")
    assert cost_resp.status_code == 200
    assert cost_resp.json()["status"] == "COST_CALCULATED"
    assert cost_resp.json()["monthlyTotal"] > 0

    detail_resp = client.get(f"/api/sessions/{session_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "COST_CALCULATED"
    assert detail["architecture"] is not None
    assert detail["terraform"] is not None
    assert detail["cost"] is not None

