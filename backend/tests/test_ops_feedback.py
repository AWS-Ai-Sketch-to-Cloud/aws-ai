from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app


def _auth_client() -> TestClient:
    fixed_user_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=fixed_user_id,
        login_id="feedback-test-user",
        email="feedback-test@example.com",
        display_name="Feedback User",
        role="USER",
    )
    return TestClient(app)


def test_repo_analysis_feedback_roundtrip() -> None:
    try:
        client = _auth_client()
        full_name = "example/repo"

        save_res = client.post(
            "/api/ops/repo-analysis-feedback",
            json={"fullName": full_name, "verdict": "APPROVE", "note": "배포 진행 가능"},
        )
        assert save_res.status_code == 200
        saved = save_res.json()
        assert saved["saved"] is True
        assert saved["verdict"] == "APPROVE"

        get_res = client.get(f"/api/ops/repo-analysis-feedback?fullName={full_name}")
        assert get_res.status_code == 200
        body = get_res.json()
        assert body["fullName"] == full_name
        assert body["feedback"] is not None
        assert body["feedback"]["verdict"] == "APPROVE"
    finally:
        app.dependency_overrides.clear()
