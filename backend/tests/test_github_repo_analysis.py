from __future__ import annotations

from app.services.github_repo_analysis import build_repo_analysis


def test_repo_analysis_recommends_ecs_for_docker_repo() -> None:
    result = build_repo_analysis(
        full_name="acme/api-service",
        default_branch="main",
        files=[
            "Dockerfile",
            "requirements.txt",
            "app/main.py",
            ".github/workflows/deploy.yml",
        ],
        file_contents={
            "readme.md": "Backend API service",
            "requirements.txt": "fastapi==0.116.1",
            ".github/workflows/deploy.yml": "name: deploy",
        },
    )

    assert result["recommendedStack"][0] == "Amazon ECS (Fargate)"
    assert result["detected"]["dockerfile"] is True
    assert result["detected"]["githubActions"] is True
    assert any("ECS Fargate" in step for step in result["deploymentSteps"])


def test_repo_analysis_recommends_amplify_for_frontend_only_repo() -> None:
    result = build_repo_analysis(
        full_name="acme/web-app",
        default_branch="main",
        files=[
            "package.json",
            "vite.config.ts",
            "src/main.tsx",
        ],
        file_contents={
            "package.json": '{"dependencies":{"react":"^19.0.0","vite":"^6.0.0"}}',
            "readme.md": "Frontend web app",
        },
    )

    assert result["recommendedStack"][0] == "AWS Amplify Hosting"
    assert "Node.js/TypeScript" in result["languageHints"]
    assert result["architecture"]["rds"]["enabled"] is False


def test_repo_analysis_steps_are_not_static_across_profiles() -> None:
    ecs_result = build_repo_analysis(
        full_name="acme/ecs-app",
        default_branch="main",
        files=["Dockerfile", "app/main.py"],
        file_contents={"readme.md": "containerized backend"},
    )
    eks_result = build_repo_analysis(
        full_name="acme/eks-app",
        default_branch="develop",
        files=["k8s/deployment.yaml", "Dockerfile", "app/main.py"],
        file_contents={"readme.md": "kubernetes deployment"},
    )

    assert ecs_result["deploymentSteps"] != eks_result["deploymentSteps"]
    assert any("EKS" in step for step in eks_result["deploymentSteps"])
