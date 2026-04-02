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
    client_ip = f"198.18.{suffix % 250}.{(suffix // 250) % 250}"
    auth_headers = {"x-forwarded-for": client_ip}

    _must(
        client.post(
            "/api/auth/register",
            headers=auth_headers,
            json={
                "loginId": login_id,
                "email": email,
                "password": password,
                "displayName": "Test User",
            },
        ),
        "register",
    )
    login = _must(
        client.post("/api/auth/login", headers=auth_headers, json={"loginId": login_id, "password": password}),
        "login",
    )
    return {"Authorization": f"Bearer {login['accessToken']}"}


def _wait_for_deployment_status(
    client: TestClient,
    headers: dict[str, str],
    session_id: str,
    action: str,
    expected: str,
    timeout_sec: int = 15,
) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        history = _must(client.get(f"/api/sessions/{session_id}/deployments", headers=headers), "deployment history")
        candidate = next((item for item in history["items"] if item["action"] == action), None)
        if candidate and candidate["status"] == expected:
            return candidate
        time.sleep(0.3)
    raise RuntimeError(f"deployment {action} did not reach {expected} within timeout")


def _create_project(client: TestClient, headers: dict[str, str], name: str, description: str = "test") -> dict:
    return _must(
        client.post("/api/projects", headers=headers, json={"name": name, "description": description}),
        "create project",
    )


def _create_session(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    input_text: str,
) -> dict:
    return _must(
        client.post(
            f"/api/projects/{project_id}/sessions",
            headers=headers,
            json={"inputType": "TEXT", "inputText": input_text},
        ),
        "create session",
    )


def _save_architecture(
    client: TestClient,
    headers: dict[str, str],
    session_id: str,
    architecture_json: dict,
) -> dict:
    return _must(
        client.post(
            f"/api/sessions/{session_id}/architecture",
            headers=headers,
            json={"schemaVersion": "v1", "architectureJson": architecture_json},
        ),
        "save architecture",
    )


def test_analyze_requires_auth() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/sessions/00000000-0000-0000-0000-000000000000/analyze",
        json={"inputText": "test", "inputType": "text"},
    )
    assert response.status_code == 401


def test_removed_legacy_session_routes_return_not_found() -> None:
    client = TestClient(app)
    create_response = client.post("/sessions", json={"project_id": "00000000-0000-0000-0000-000000000000"})
    detail_response = client.get("/sessions/00000000-0000-0000-0000-000000000000")
    analyze_response = client.post(
        "/sessions/00000000-0000-0000-0000-000000000000/analyze",
        json={"inputText": "test", "inputType": "text"},
    )

    assert create_response.status_code == 404
    assert detail_response.status_code == 404
    assert analyze_response.status_code == 404


def test_project_list_and_session_list_return_saved_history() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)

    project_a = _create_project(client, headers, "history-proj-a")
    project_b = _create_project(client, headers, "history-proj-b")

    session_v1 = _create_session(client, headers, project_a["projectId"], "first draft")
    session_v2 = _create_session(client, headers, project_a["projectId"], "second draft")
    _create_session(client, headers, project_b["projectId"], "other project draft")

    project_list = _must(client.get("/api/projects", headers=headers), "list projects")
    listed_project_ids = [item["projectId"] for item in project_list["items"]]

    assert project_a["projectId"] in listed_project_ids
    assert project_b["projectId"] in listed_project_ids

    session_list = _must(
        client.get(f"/api/projects/{project_a['projectId']}/sessions", headers=headers),
        "list project sessions",
    )

    assert [item["versionNo"] for item in session_list["items"]] == [2, 1]
    assert session_list["items"][0]["sessionId"] == session_v2["sessionId"]
    assert session_list["items"][1]["sessionId"] == session_v1["sessionId"]
    assert all(item["status"] == "CREATED" for item in session_list["items"])


def test_compare_uses_selected_base_session_and_returns_detailed_diff() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)

    project = _create_project(client, headers, "compare-proj")
    base_session = _create_session(client, headers, project["projectId"], "baseline")
    target_session = _create_session(client, headers, project["projectId"], "optimized")

    _save_architecture(
        client,
        headers,
        base_session["sessionId"],
        {
            "vpc": True,
            "ec2": {"count": 1, "instance_type": "t3.small"},
            "rds": {"enabled": True, "engine": "mysql"},
            "bedrock": {"enabled": False, "model": None},
            "additional_services": [],
            "usage": {"monthly_hours": 730, "data_transfer_gb": 5, "storage_gb": 20, "requests_million": 1},
            "public": False,
            "region": "ap-northeast-2",
        },
    )
    _save_architecture(
        client,
        headers,
        target_session["sessionId"],
        {
            "vpc": True,
            "ec2": {"count": 2, "instance_type": "t3.medium"},
            "rds": {"enabled": True, "engine": "mysql"},
            "bedrock": {"enabled": False, "model": None},
            "additional_services": ["alb"],
            "usage": {"monthly_hours": 730, "data_transfer_gb": 10, "storage_gb": 50, "requests_million": 2},
            "public": False,
            "region": "ap-northeast-2",
        },
    )

    _must(client.post(f"/api/sessions/{base_session['sessionId']}/terraform", headers=headers), "terraform base")
    _must(client.post(f"/api/sessions/{target_session['sessionId']}/terraform", headers=headers), "terraform target")
    _must(client.post(f"/api/sessions/{base_session['sessionId']}/cost", headers=headers), "cost base")
    _must(client.post(f"/api/sessions/{target_session['sessionId']}/cost", headers=headers), "cost target")

    compare = _must(
        client.get(
            f"/api/sessions/{target_session['sessionId']}/compare?baseSessionId={base_session['sessionId']}",
            headers=headers,
        ),
        "compare sessions",
    )

    assert compare["baseSession"]["sessionId"] == base_session["sessionId"]
    assert compare["targetSession"]["sessionId"] == target_session["sessionId"]
    assert any(
        item["path"] == "$.additional_services" and item["changeType"] == "changed"
        for item in compare["jsonDiff"]
    )
    assert any(item["path"] == "$.ec2.count" and item["changeType"] == "changed" for item in compare["jsonDiff"])
    assert compare["terraformDiff"]["changed"] is True
    assert "base.tf" in compare["terraformDiff"]["diff"]
    assert "target.tf" in compare["terraformDiff"]["diff"]
    assert "monthlyTotal" in compare["costDiff"]
    assert "breakdown" in compare["costDiff"]
    assert isinstance(compare["costDiff"]["assumptionsChanged"], list)


def test_cost_contains_optimization_summary() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)

    project = _create_project(client, headers, "test-proj")
    session = _create_session(client, headers, project["projectId"], "baseline")
    session_id = session["sessionId"]

    _save_architecture(
        client,
        headers,
        session_id,
        {
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


def test_project_session_access_is_forbidden_for_other_user() -> None:
    client = TestClient(app)
    owner_headers = _create_auth_headers(client)
    other_headers = _create_auth_headers(client)

    project = _create_project(client, owner_headers, "owner-only-project")
    create_by_other = client.post(
        f"/api/projects/{project['projectId']}/sessions",
        headers=other_headers,
        json={"inputType": "TEXT", "inputText": "should fail"},
    )
    list_by_other = client.get(f"/api/projects/{project['projectId']}/sessions", headers=other_headers)

    assert create_by_other.status_code == 403
    assert list_by_other.status_code == 403


def test_invalid_status_transition_returns_409() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)
    project = _create_project(client, headers, "transition-project")
    session = _create_session(client, headers, project["projectId"], "invalid transition check")

    response = client.patch(
        f"/api/sessions/{session['sessionId']}/status",
        headers=headers,
        json={"status": "GENERATED"},
    )

    assert response.status_code == 409
    assert "invalid status transition" in response.json().get("detail", "")


def test_deploy_destroy_and_list_history_in_simulation_mode() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)

    project = _create_project(client, headers, "deploy-proj")
    session = _create_session(client, headers, project["projectId"], "deploy baseline")
    session_id = session["sessionId"]

    _save_architecture(
        client,
        headers,
        session_id,
        {
            "vpc": True,
            "ec2": {"count": 1, "instance_type": "t3.micro"},
            "rds": {"enabled": False, "engine": None},
            "bedrock": {"enabled": False, "model": None},
            "additional_services": [],
            "usage": {"monthly_hours": 730, "data_transfer_gb": 1, "storage_gb": 10, "requests_million": 1},
            "public": False,
            "region": "ap-northeast-2",
        },
    )
    _must(client.post(f"/api/sessions/{session_id}/terraform", headers=headers), "terraform")

    deploy = _must(
        client.post(
            f"/api/sessions/{session_id}/deploy",
            headers=headers,
            json={
                "awsRegion": "ap-northeast-2",
                "simulate": True,
            },
        ),
        "deploy",
    )
    assert deploy["item"]["action"] == "DEPLOY"
    assert deploy["item"]["status"] in {"PENDING", "RUNNING", "SUCCEEDED"}
    _wait_for_deployment_status(client, headers, session_id, "DEPLOY", "SUCCEEDED")

    destroy = _must(
        client.post(
            f"/api/sessions/{session_id}/destroy",
            headers=headers,
            json={
                "awsRegion": "ap-northeast-2",
                "simulate": True,
                "confirmDestroy": True,
                "confirmationCode": f"DESTROY-{session_id.replace('-', '')[-6:].upper()}",
            },
        ),
        "destroy",
    )
    assert destroy["item"]["action"] == "DESTROY"
    assert destroy["item"]["status"] in {"PENDING", "RUNNING", "SUCCEEDED"}
    _wait_for_deployment_status(client, headers, session_id, "DESTROY", "SUCCEEDED")

    history = _must(client.get(f"/api/sessions/{session_id}/deployments", headers=headers), "deployment history")
    assert len(history["items"]) >= 2
    actions = {item["action"] for item in history["items"]}
    assert "DEPLOY" in actions
    assert "DESTROY" in actions


def test_destroy_requires_confirmation_code() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)
    project = _create_project(client, headers, "destroy-confirm-proj")
    session = _create_session(client, headers, project["projectId"], "destroy confirm")
    session_id = session["sessionId"]

    _save_architecture(
        client,
        headers,
        session_id,
        {
            "vpc": True,
            "ec2": {"count": 1, "instance_type": "t3.micro"},
            "rds": {"enabled": False, "engine": None},
            "bedrock": {"enabled": False, "model": None},
            "additional_services": [],
            "usage": {"monthly_hours": 730, "data_transfer_gb": 1, "storage_gb": 10, "requests_million": 1},
            "public": False,
            "region": "ap-northeast-2",
        },
    )
    _must(client.post(f"/api/sessions/{session_id}/terraform", headers=headers), "terraform")

    response = client.post(
        f"/api/sessions/{session_id}/destroy",
        headers=headers,
        json={
            "awsRegion": "ap-northeast-2",
            "simulate": True,
            "confirmDestroy": True,
            "confirmationCode": "WRONG-CODE",
        },
    )
    assert response.status_code == 400


def test_deploy_requires_saved_aws_config_for_real_mode() -> None:
    client = TestClient(app)
    headers = _create_auth_headers(client)

    project = _create_project(client, headers, "deploy-realmode-proj")
    session = _create_session(client, headers, project["projectId"], "deploy real mode")
    session_id = session["sessionId"]

    _save_architecture(
        client,
        headers,
        session_id,
        {
            "vpc": True,
            "ec2": {"count": 1, "instance_type": "t3.micro"},
            "rds": {"enabled": False, "engine": None},
            "bedrock": {"enabled": False, "model": None},
            "additional_services": [],
            "usage": {"monthly_hours": 730, "data_transfer_gb": 1, "storage_gb": 10, "requests_million": 1},
            "public": False,
            "region": "ap-northeast-2",
        },
    )
    _must(client.post(f"/api/sessions/{session_id}/terraform", headers=headers), "terraform")

    deploy_res = client.post(
        f"/api/sessions/{session_id}/deploy",
        headers=headers,
        json={"awsRegion": "ap-northeast-2", "simulate": False},
    )
    assert deploy_res.status_code == 400
    assert "deploy role is not configured" in deploy_res.json().get("detail", "")
