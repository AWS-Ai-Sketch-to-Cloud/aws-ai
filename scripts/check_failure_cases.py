from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


def require_env() -> None:
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is required")


def main() -> None:
    require_env()
    client = TestClient(app)

    proj = client.post("/api/projects", json={"name": "failure-check", "description": "failure scenarios"})
    project_id = proj.json()["projectId"]

    # 1) Terraform before architecture -> 409
    s1 = client.post(
        f"/api/projects/{project_id}/sessions",
        json={"inputType": "TEXT", "inputText": "EC2 1"},
    )
    session_1 = s1.json()["sessionId"]
    tf = client.post(f"/api/sessions/{session_1}/terraform")
    print("terraform_without_architecture", tf.status_code)

    # 2) Cost before architecture -> 409
    cost = client.post(f"/api/sessions/{session_1}/cost")
    print("cost_without_architecture", cost.status_code)

    # 3) Invalid architecture schema -> 422 and FAILED
    s2 = client.post(
        f"/api/projects/{project_id}/sessions",
        json={"inputType": "TEXT", "inputText": "EC2 2"},
    )
    session_2 = s2.json()["sessionId"]
    bad_arch = {
        "schemaVersion": "v1",
        "architectureJson": {
            "vpc": True,
            "ec2": {"instance_type": "t3.micro"},  # missing ec2.count
            "rds": {"enabled": False, "engine": None},
            "public": False,
            "region": "ap-northeast-2",
        },
    }
    arch_resp = client.post(f"/api/sessions/{session_2}/architecture", json=bad_arch)
    detail = client.get(f"/api/sessions/{session_2}").json()
    print("invalid_architecture_status", arch_resp.status_code)
    print("invalid_architecture_session_status", detail["status"])
    print("invalid_architecture_error_code", detail["error"]["code"] if detail.get("error") else None)


if __name__ == "__main__":
    main()

