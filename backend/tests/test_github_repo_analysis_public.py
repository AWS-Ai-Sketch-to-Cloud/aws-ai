from __future__ import annotations

from types import SimpleNamespace

from app.routers import github as github_router
from app.schemas.github import GitHubRepoAnalyzeRequest


def _sample_architecture() -> dict:
    return {
        "vpc": True,
        "ec2": {"count": 1, "instance_type": "t3.micro"},
        "rds": {"enabled": False, "engine": None},
        "bedrock": {"enabled": False, "model": None},
        "additional_services": ["s3"],
        "usage": {
            "monthly_hours": 730,
            "data_transfer_gb": 60,
            "storage_gb": 10,
            "requests_million": 2,
        },
        "public": True,
        "region": "ap-northeast-2",
    }


def test_repo_analysis_allows_public_repo_without_github_token(monkeypatch) -> None:
    monkeypatch.setattr(github_router, "REPO_ANALYSIS_AI_ONLY", False)
    monkeypatch.setattr(github_router, "_ensure_repo_analysis_ai_ready", lambda: None)
    monkeypatch.setattr(github_router, "get_github_access_token", lambda db, user_id: None)
    monkeypatch.setattr(
        github_router,
        "_github_request",
        lambda path, access_token=None: (
            {"default_branch": "main", "description": "public repo", "topics": ["demo"]}
            if path == "/repos/acme/public-repo"
            else {"tree": [{"path": "README.md", "type": "blob"}]}
        ),
    )
    monkeypatch.setattr(github_router, "_collect_file_contents", lambda **kwargs: {"readme.md": "# demo"})
    monkeypatch.setattr(
        github_router,
        "_run_ai_analysis",
        lambda **kwargs: (
            _sample_architecture(),
            {"provider": "bedrock", "fallbackUsed": False, "requirementCoverage": 0.9},
            {
                "summary": "public repo summary",
                "findings": ["finding"],
                "recommendedStack": ["Amazon S3"],
                "deploymentSteps": ["step"],
                "risks": ["risk"],
                "costNotes": ["note"],
            },
            0.92,
            "high",
            "bedrock",
            False,
            ["README.md"],
        ),
    )
    monkeypatch.setattr(github_router, "get_cached_analysis", lambda key: None)
    monkeypatch.setattr(github_router, "put_cached_analysis", lambda key, payload: None)

    response = github_router.analyze_github_repo(
        GitHubRepoAnalyzeRequest(fullName="acme/public-repo"),
        db=None,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.fullName == "acme/public-repo"
    assert response.defaultBranch == "main"
    assert response.cacheHit is False
