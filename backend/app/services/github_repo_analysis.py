from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RepoSignal:
    has_dockerfile: bool
    has_k8s_manifests: bool
    has_serverless_config: bool
    has_terraform: bool
    has_cdk: bool
    has_frontend_framework: bool
    has_backend_runtime: bool
    has_github_actions: bool
    has_readme: bool
    package_json: dict[str, Any] | None
    language_hints: list[str]
    dependency_files: list[str]


def _path_set(files: list[str]) -> set[str]:
    return {path.lower() for path in files}


def _has_suffix(paths: set[str], suffix: str) -> bool:
    sfx = suffix.lower()
    return any(path.endswith(sfx) for path in paths)


def _parse_package_json(file_contents: dict[str, str]) -> dict[str, Any] | None:
    raw = file_contents.get("package.json")
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _contains_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in words)


def _detect_signals(files: list[str], file_contents: dict[str, str]) -> RepoSignal:
    paths = _path_set(files)
    package_json = _parse_package_json(file_contents)

    dependency_files = [
        path
        for path in files
        if path.lower().split("/")[-1]
        in {
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "pom.xml",
            "build.gradle",
            "go.mod",
            "cargo.toml",
        }
    ]

    language_hints: list[str] = []
    if "package.json" in {f.split("/")[-1].lower() for f in files}:
        language_hints.append("Node.js/TypeScript")
    if _has_suffix(paths, "requirements.txt") or _has_suffix(paths, "pyproject.toml"):
        language_hints.append("Python")
    if _has_suffix(paths, "pom.xml") or _has_suffix(paths, "build.gradle"):
        language_hints.append("Java")
    if _has_suffix(paths, "go.mod"):
        language_hints.append("Go")
    if _has_suffix(paths, "cargo.toml"):
        language_hints.append("Rust")

    readme_text = file_contents.get("readme.md", "")
    workflows_text = "\n".join(
        content
        for path, content in file_contents.items()
        if path.startswith(".github/workflows/") and content
    )

    return RepoSignal(
        has_dockerfile=_has_suffix(paths, "dockerfile"),
        has_k8s_manifests=any(path.endswith((".yaml", ".yml")) and "k8s" in path for path in paths)
        or any("/kubernetes/" in path for path in paths),
        has_serverless_config=_has_suffix(paths, "serverless.yml")
        or _has_suffix(paths, "template.yaml")
        or _has_suffix(paths, "template.yml"),
        has_terraform=any(path.endswith(".tf") for path in paths),
        has_cdk=_has_suffix(paths, "cdk.json"),
        has_frontend_framework=_has_suffix(paths, "next.config.js")
        or _has_suffix(paths, "next.config.mjs")
        or _has_suffix(paths, "vite.config.ts")
        or _has_suffix(paths, "vite.config.js"),
        has_backend_runtime=_has_suffix(paths, "main.py")
        or _has_suffix(paths, "app.py")
        or _has_suffix(paths, "pom.xml")
        or _has_suffix(paths, "go.mod")
        or _has_suffix(paths, "server.js")
        or _contains_any(readme_text, ["api", "backend", "fastapi", "express"]),
        has_github_actions=any(path.startswith(".github/workflows/") for path in paths),
        has_readme=_has_suffix(paths, "readme.md"),
        package_json=package_json,
        language_hints=language_hints,
        dependency_files=dependency_files[:20],
    )


def _pick_region(default_branch: str, file_contents: dict[str, str]) -> str:
    hints = f"{default_branch}\n" + "\n".join(list(file_contents.values())[:5])
    if "ap-northeast-2" in hints:
        return "ap-northeast-2"
    if "us-east-1" in hints:
        return "us-east-1"
    return "ap-northeast-2"


def _select_ec2_type(signals: RepoSignal) -> str:
    package_json = signals.package_json or {}
    deps = {**(package_json.get("dependencies") or {}), **(package_json.get("devDependencies") or {})}
    dep_names = {str(k).lower() for k in deps.keys()}
    if "next" in dep_names or "react" in dep_names:
        return "t3.small"
    if "fastapi" in dep_names or "django" in dep_names:
        return "t3.micro"
    if signals.has_k8s_manifests:
        return "t3.medium"
    return "t3.micro"


def _estimate_usage(signals: RepoSignal) -> dict[str, float]:
    if signals.has_k8s_manifests:
        return {"monthly_hours": 730, "requests_million": 18, "storage_gb": 200, "data_transfer_gb": 600}
    if signals.has_frontend_framework and not signals.has_backend_runtime:
        return {"monthly_hours": 730, "requests_million": 12, "storage_gb": 120, "data_transfer_gb": 420}
    if signals.has_serverless_config:
        return {"monthly_hours": 730, "requests_million": 8, "storage_gb": 40, "data_transfer_gb": 200}
    return {"monthly_hours": 730, "requests_million": 5, "storage_gb": 60, "data_transfer_gb": 140}


def _build_architecture(full_name: str, default_branch: str, signals: RepoSignal, file_contents: dict[str, str]) -> dict[str, Any]:
    additional_services: list[str] = ["cloudwatch"]
    if signals.has_frontend_framework:
        additional_services.extend(["cloudfront", "route53", "s3"])
    if signals.has_backend_runtime:
        additional_services.append("alb")
    if signals.has_k8s_manifests:
        additional_services.extend(["eks", "ecr", "waf"])
    elif signals.has_dockerfile:
        additional_services.extend(["ecs", "ecr"])
    elif signals.has_serverless_config:
        additional_services.extend(["lambda", "apigateway"])

    readme_text = file_contents.get("readme.md", "").lower()
    if _contains_any(readme_text, ["redis", "cache"]):
        additional_services.append("elasticache")
    if _contains_any(readme_text, ["queue", "worker", "async"]):
        additional_services.append("sqs")

    package_json = signals.package_json or {}
    deps = {**(package_json.get("dependencies") or {}), **(package_json.get("devDependencies") or {})}
    dep_names = {str(k).lower() for k in deps.keys()}
    wants_db = signals.has_backend_runtime or _contains_any(readme_text, ["postgres", "mysql", "database", "rds"])
    rds_engine = "postgres" if any(name in dep_names for name in {"pg", "psycopg", "typeorm"}) else "mysql"
    if _contains_any(readme_text, ["postgres", "postgresql"]):
        rds_engine = "postgres"

    architecture = {
        "name": full_name,
        "region": _pick_region(default_branch, file_contents),
        "public": True,
        "ec2": {
            "count": 2 if signals.has_backend_runtime else 1,
            "instance_type": _select_ec2_type(signals),
        },
        "rds": {"enabled": wants_db, "engine": rds_engine if wants_db else None},
        "bedrock": {"enabled": False, "model": None},
        "additional_services": sorted(set(additional_services)),
        "usage": _estimate_usage(signals),
    }
    return architecture


def _dynamic_deployment_steps(
    *,
    default_branch: str,
    signals: RepoSignal,
    architecture: dict[str, Any],
) -> list[str]:
    steps: list[str] = []

    if signals.has_terraform:
        steps.append("기존 Terraform 모듈과 상태 백엔드(S3 + DynamoDB lock) 구조를 먼저 정리")
    elif signals.has_cdk:
        steps.append("CDK 스택을 dev/stage/prod로 분리하고 계정별 bootstrap 재적용")
    else:
        steps.append("현재 레포 기준 IaC 템플릿(Terraform) 신규 생성 및 환경 변수화")

    services = set(str(s).lower() for s in architecture.get("additional_services", []))
    if "eks" in services:
        steps.append("EKS 기준으로 ECR 이미지 빌드/푸시 후 Helm 또는 Kustomize 배포 파이프라인 구성")
    elif "ecs" in services:
        steps.append("ECS Fargate 기준 Task Definition/Service/ALB 롤링 배포 단계 구성")
    elif "lambda" in services:
        steps.append("Lambda + API Gateway 기준 버전/alias canary 배포 정책 구성")
    else:
        steps.append("애플리케이션 유형에 맞춘 배포 타깃을 명시하고 배포 자동화 구성")

    if signals.has_github_actions:
        steps.append("기존 GitHub Actions에 AWS OIDC + 환경별 승인 게이트를 추가")
    else:
        steps.append("GitHub Actions CI/CD를 신설해 테스트-보안스캔-배포를 자동화")

    protected_branch = default_branch or "main"
    steps.append(f"`{protected_branch}` 브랜치 보호 + PR 승인 + 배포 전 수동 승인 정책 적용")
    steps.append("애플리케이션 시크릿은 Secrets Manager/SSM으로 이전하고 런타임 주입 방식으로 전환")
    return steps


def _dynamic_risks(signals: RepoSignal, architecture: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    services = set(str(s).lower() for s in architecture.get("additional_services", []))
    if not signals.has_github_actions:
        risks.append("CI/CD 파이프라인 부재 가능성으로 배포 휴먼에러 위험이 높습니다.")
    if not signals.has_terraform and not signals.has_cdk:
        risks.append("IaC가 없어 운영 환경 재현성과 변경 추적이 약합니다.")
    if "eks" in services and not signals.has_k8s_manifests:
        risks.append("EKS 선택 대비 쿠버네티스 매니페스트가 부족해 런타임 구성 누락 위험이 있습니다.")
    if "alb" in services and "waf" not in services and architecture.get("public"):
        risks.append("공개 엔드포인트에 WAF 부재 시 L7 공격 면적이 커질 수 있습니다.")
    if architecture.get("rds", {}).get("enabled") and architecture.get("rds", {}).get("engine") is None:
        risks.append("RDS 엔진이 명확하지 않아 마이그레이션/드라이버 호환 리스크가 있습니다.")
    return risks


def build_repo_analysis(
    *,
    full_name: str,
    default_branch: str,
    files: list[str],
    file_contents: dict[str, str],
) -> dict[str, Any]:
    signals = _detect_signals(files, file_contents)
    architecture = _build_architecture(full_name, default_branch, signals, file_contents)
    deployment_steps = _dynamic_deployment_steps(
        default_branch=default_branch,
        signals=signals,
        architecture=architecture,
    )
    risks = _dynamic_risks(signals, architecture)

    services = set(str(s) for s in architecture.get("additional_services", []))
    if "eks" in services:
        recommended_stack = ["Amazon EKS", "Amazon ECR", "Application Load Balancer"]
    elif "ecs" in services:
        recommended_stack = ["Amazon ECS (Fargate)", "Amazon ECR", "Application Load Balancer"]
    elif "lambda" in services:
        recommended_stack = ["AWS Lambda", "Amazon API Gateway", "Amazon CloudWatch"]
    elif signals.has_frontend_framework and not signals.has_backend_runtime:
        recommended_stack = ["AWS Amplify Hosting", "Amazon CloudFront", "Amazon S3"]
    else:
        recommended_stack = ["Amazon ECS (Fargate)", "Amazon ECR", "Application Load Balancer", "Amazon RDS"]

    required_services = sorted(set(recommended_stack + ["AWS IAM", "Amazon CloudWatch"] + list(services)))
    cost_notes: list[str] = []
    if "Amazon EKS" in recommended_stack:
        cost_notes.append("EKS 제어 플레인 고정비가 있어 소규모 서비스에는 과한 비용일 수 있습니다.")
    if architecture.get("rds", {}).get("enabled"):
        cost_notes.append("RDS 운영 시 백업/스토리지/트래픽에 따라 월 비용 편차가 큽니다.")
    if "Amazon ECS (Fargate)" in recommended_stack:
        cost_notes.append("Fargate는 운영 단순화 이점이 있으나 EC2 대비 단가가 높을 수 있습니다.")
    if "AWS Lambda" in recommended_stack:
        cost_notes.append("요청량 급증 시 API Gateway + Lambda 요청비가 빠르게 증가할 수 있습니다.")

    findings: list[str] = []
    if signals.has_dockerfile:
        findings.append("Dockerfile이 있어 컨테이너 기반 배포 준비도가 높습니다.")
    if signals.has_k8s_manifests:
        findings.append("K8s 매니페스트가 있어 EKS 이행 경로가 명확합니다.")
    if signals.has_github_actions:
        findings.append("GitHub Actions 워크플로우가 존재해 CI/CD 확장이 용이합니다.")
    if not findings:
        findings.append("명확한 배포 신호 파일이 적어 보수적 기본 아키텍처를 제안했습니다.")

    summary = (
        f"{full_name} 레포를 파일 구조와 핵심 설정 기준으로 분석한 결과, "
        f"기본 권장 배포 타깃은 {recommended_stack[0]} 입니다."
    )

    return {
        "summary": summary,
        "findings": findings,
        "recommendedStack": recommended_stack,
        "requiredServices": required_services,
        "languageHints": signals.language_hints,
        "dependencyFiles": signals.dependency_files,
        "deploymentSteps": deployment_steps,
        "risks": risks,
        "costNotes": cost_notes,
        "architecture": architecture,
        "detected": {
            "dockerfile": signals.has_dockerfile,
            "k8sManifests": signals.has_k8s_manifests,
            "serverlessConfig": signals.has_serverless_config,
            "terraform": signals.has_terraform,
            "cdk": signals.has_cdk,
            "githubActions": signals.has_github_actions,
            "readme": signals.has_readme,
        },
    }
