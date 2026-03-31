from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app


def _auth_client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(),
        login_id="ops-test-user",
        email="ops-test@example.com",
        display_name="Ops User",
        role="USER",
    )
    return TestClient(app)


def test_repo_analysis_health_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/ops/repo-analysis-health")
    assert response.status_code == 401


def test_repo_analysis_health_shape() -> None:
    try:
        client = _auth_client()
        response = client.get("/api/ops/repo-analysis-health")
        assert response.status_code == 200
        body = response.json()
        assert "policy" in body
        assert "cache" in body
        assert "failures" in body
        assert "recommendations" in body
    finally:
        app.dependency_overrides.clear()


def test_repo_analysis_readiness_shape() -> None:
    try:
        client = _auth_client()
        response = client.get("/api/ops/readiness")
        assert response.status_code == 200
        body = response.json()
        assert "score" in body
        assert "grade" in body
        assert "checklist" in body
    finally:
        app.dependency_overrides.clear()
