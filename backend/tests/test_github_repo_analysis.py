from __future__ import annotations

from app.services.github_ai_report import generate_repo_report_with_ai
from app.routers.github import _build_confidence


def _sample_architecture() -> dict:
    return {
        "vpc": True,
        "ec2": {"count": 1, "instance_type": "t3.micro"},
        "rds": {"enabled": False, "engine": None},
        "bedrock": {"enabled": False, "model": None},
        "additional_services": ["s3", "cloudfront", "route53"],
        "usage": {
            "monthly_hours": 730,
            "data_transfer_gb": 60,
            "storage_gb": 10,
            "requests_million": 2,
        },
        "public": True,
        "region": "ap-northeast-2",
    }


def test_ai_report_fallback_when_bedrock_disabled(monkeypatch) -> None:
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_STRICT_MODE", "false")
    monkeypatch.setenv("BEDROCK_FALLBACK_ENABLED", "true")
    report, meta = generate_repo_report_with_ai(
        repo_prompt="Repository: acme/acme.github.io",
        architecture=_sample_architecture(),
        model_rationale={"summary": "static profile"},
    )

    assert report["summary"]
    assert report["recommendedStack"]
    assert report["deploymentSteps"]
    assert report["costNotes"]
    assert meta["provider"] == "local_fallback"
    assert meta["fallbackUsed"] is True


def test_ai_report_fallback_contains_beginner_steps(monkeypatch) -> None:
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_STRICT_MODE", "false")
    monkeypatch.setenv("BEDROCK_FALLBACK_ENABLED", "true")
    report, _ = generate_repo_report_with_ai(
        repo_prompt="Repository: acme/simple-web",
        architecture=_sample_architecture(),
        model_rationale={},
    )

    assert any("배포" in step or "파이프라인" in step for step in report["deploymentSteps"])


def test_ai_report_strict_mode_blocks_fallback(monkeypatch) -> None:
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_STRICT_MODE", "true")
    monkeypatch.setenv("BEDROCK_FALLBACK_ENABLED", "false")

    try:
        generate_repo_report_with_ai(
            repo_prompt="Repository: acme/simple-web",
            architecture=_sample_architecture(),
            model_rationale={},
        )
        assert False, "strict mode should raise when bedrock is disabled"
    except RuntimeError as exc:
        assert "BEDROCK_ENABLED" in str(exc)


def test_confidence_scoring_and_label() -> None:
    score, label, provider, fallback_used = _build_confidence(
        analysis_meta={"provider": "bedrock", "fallbackUsed": False, "requirementCoverage": 0.9},
        detected_flags={"dockerfile": True, "k8sManifests": False, "serverlessConfig": False, "terraform": True, "cdk": False, "githubActions": True, "readme": True},
        evidence_files=["readme.md", "package.json", "dockerfile", ".github/workflows/deploy.yml"],
    )
    assert 0 <= score <= 1
    assert label in {"높음", "중간", "낮음"}
    assert provider == "bedrock"
    assert fallback_used is False
