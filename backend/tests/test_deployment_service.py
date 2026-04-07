from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from app.services.deployment_service import AwsCredentials, run_deploy, run_destroy


def _write_fake_terraform(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "@echo off",
                "set CMD=%1",
                "if \"%CMD%\"==\"version\" goto :version",
                "if \"%CMD%\"==\"init\" goto :init",
                "if \"%CMD%\"==\"apply\" goto :apply",
                "if \"%CMD%\"==\"output\" goto :output",
                "if \"%CMD%\"==\"destroy\" goto :destroy",
                "echo unsupported command",
                "exit /b 1",
                ":version",
                "echo Terraform v0.fake",
                "exit /b 0",
                ":init",
                "echo init ok",
                "exit /b 0",
                ":apply",
                "echo {\"resources\":[{\"name\":\"example\"}]} > terraform.tfstate",
                "echo apply ok",
                "exit /b 0",
                ":output",
                "echo {\"service_url\":{\"value\":\"https://example.test\"}}",
                "exit /b 0",
                ":destroy",
                "if exist terraform.tfstate del /q terraform.tfstate",
                "if exist terraform.tfstate.backup del /q terraform.tfstate.backup",
                "echo destroy ok",
                "exit /b 0",
            ]
        ),
        encoding="utf-8",
    )


def _make_test_dir() -> Path:
    root = Path(__file__).resolve().parents[2] / ".test-artifacts" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_run_deploy_persists_state_and_outputs(monkeypatch) -> None:
    tmp_path = _make_test_dir()
    fake_terraform = tmp_path / "terraform.cmd"
    _write_fake_terraform(fake_terraform)
    state_root = tmp_path / "state-root"

    try:
        monkeypatch.setenv("DEPLOY_STATE_DIR", str(state_root))
        monkeypatch.setattr("app.services.deployment_service._resolve_terraform_bin", lambda: str(fake_terraform))
        monkeypatch.setattr("app.services.deployment_service._assert_allowed_account", lambda credentials, region: "123456789012")

        result = run_deploy(
            terraform_code='resource "null_resource" "example" {}',
            credentials=AwsCredentials("key", "secret", "token"),
            region="us-east-1",
            state_key="session-123",
            simulate=False,
        )

        assert result.status == "SUCCEEDED"
        assert result.resources is not None
        assert result.resources["accountId"] == "123456789012"
        assert result.resources["statePreserved"] is True
        assert result.resources["stateExistedBefore"] is False
        assert Path(str(result.resources["stateFile"])).exists()
        assert Path(str(result.resources["stateDir"])) == state_root / "session-123"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_run_destroy_requires_saved_state_and_cleans_up(monkeypatch) -> None:
    tmp_path = _make_test_dir()
    fake_terraform = tmp_path / "terraform.cmd"
    _write_fake_terraform(fake_terraform)
    state_root = tmp_path / "state-root"

    try:
        monkeypatch.setenv("DEPLOY_STATE_DIR", str(state_root))
        monkeypatch.setattr("app.services.deployment_service._resolve_terraform_bin", lambda: str(fake_terraform))
        monkeypatch.setattr("app.services.deployment_service._assert_allowed_account", lambda credentials, region: "123456789012")

        credentials = AwsCredentials("key", "secret", "token")
        no_state = run_destroy(
            terraform_code='resource "null_resource" "example" {}',
            credentials=credentials,
            region="us-east-1",
            state_key="missing-session",
            simulate=False,
        )
        assert no_state.status == "FAILED"
        assert "no saved terraform state found" in no_state.log

        deployed = run_deploy(
            terraform_code='resource "null_resource" "example" {}',
            credentials=credentials,
            region="us-east-1",
            state_key="session-456",
            simulate=False,
        )
        assert deployed.status == "SUCCEEDED"

        destroyed = run_destroy(
            terraform_code='resource "null_resource" "example" {}',
            credentials=credentials,
            region="us-east-1",
            state_key="session-456",
            simulate=False,
        )
        assert destroyed.status == "SUCCEEDED"
        assert destroyed.resources is not None
        assert destroyed.resources["destroyed"] is True
        assert destroyed.resources["stateExistedBefore"] is True
        assert destroyed.resources["statePreserved"] is False
        assert not Path(str(deployed.resources["stateFile"])).exists()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
