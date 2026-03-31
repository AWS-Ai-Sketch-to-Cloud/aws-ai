from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai_parser import AIParseError, parse_architecture_with_retry
from app.core.constants import ARCH_SCHEMA
from app.core.deps import get_current_user
from app.cost_calculator import estimate_monthly_cost
from app.database import get_db
from app.models import User
from app.schemas.github import (
    GitHubConnectionStatusResponse,
    GitHubRepoAnalyzeRequest,
    GitHubRepoAnalyzeResponse,
    GitHubRepoItem,
    GitHubRepoListResponse,
)
from app.services.github_ai_report import generate_repo_report_with_ai
from app.services.github_analysis_cache import get_cached_analysis, put_cached_analysis
from app.services.analysis_failure_logger import log_repo_analysis_failure
from app.services.github_oauth_store import get_github_access_token
from app.terraform_generator import generate_terraform_from_architecture

router = APIRouter()

MAX_CONTENT_FILES = 12
MAX_CONTENT_FILES_RETRY = 24
MAX_CONTENT_FILES_DEEP = 36
MAX_CONTENT_BYTES = 80_000
MAX_FILE_LIST_ITEMS = 200
MAX_SNIPPET_CHARS = 2500
INTERESTING_FILE_NAMES = {
    "readme.md",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "go.mod",
    "cargo.toml",
    "dockerfile",
    "serverless.yml",
    "serverless.yaml",
    "cdk.json",
    "docker-compose.yml",
    "docker-compose.yaml",
}
PRIORITY_FILE_PATTERNS = [
    "readme.md",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "serverless.yml",
    "serverless.yaml",
    "cdk.json",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "pom.xml",
    "go.mod",
    "cargo.toml",
]

CONFIDENCE_LABEL_HIGH = "높음"
CONFIDENCE_LABEL_MEDIUM = "중간"
CONFIDENCE_LABEL_LOW = "낮음"
CONFIDENCE_RETRY_THRESHOLD = float(os.getenv("GITHUB_ANALYSIS_RETRY_THRESHOLD", "0.72"))
REPO_ANALYSIS_AI_ONLY = os.getenv("GITHUB_REPO_ANALYSIS_AI_ONLY", "true").lower() == "true"


def _github_request(path: str, *, access_token: str) -> dict | list:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "Sketch-to-Cloud",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise HTTPException(
                status_code=401,
                detail="GitHub 토큰이 만료되었거나 권한이 부족합니다. GitHub로 다시 로그인해 주세요.",
            ) from exc
        if exc.code == 404:
            raise HTTPException(status_code=404, detail="GitHub 리소스를 찾을 수 없습니다.") from exc
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=502, detail=f"GitHub API 호출 실패: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail="GitHub API와 통신할 수 없습니다.") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="GitHub 응답을 해석할 수 없습니다.") from exc


def _require_github_token(db: Session, user: User) -> str:
    token = get_github_access_token(db, user.id)
    if not token:
        raise HTTPException(
            status_code=409,
            detail="현재 세션에 GitHub 접근 토큰이 없습니다. GitHub 소셜 로그인으로 다시 로그인해 주세요.",
        )
    return token


def _github_oauth_configured() -> bool:
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID") or os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET") or os.getenv("GITHUB_CLIENT_SECRET")
    return bool(client_id and client_secret)


def _validate_repo_full_name(full_name: str) -> str:
    parts = full_name.strip().split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HTTPException(status_code=400, detail="fullName은 owner/repo 형식이어야 합니다.")
    return f"{parts[0]}/{parts[1]}"


def _decode_blob_content(blob: dict[str, Any]) -> str:
    encoding = str(blob.get("encoding", "")).lower()
    content = blob.get("content")
    if encoding != "base64" or not isinstance(content, str):
        return ""
    try:
        raw = base64.b64decode(content.encode("utf-8"), validate=False)
    except Exception:
        return ""
    if len(raw) > MAX_CONTENT_BYTES:
        return ""
    return raw.decode("utf-8", errors="ignore")


def _collect_file_contents(
    *,
    encoded_full_name: str,
    access_token: str,
    tree_items: list[dict[str, Any]],
    max_files: int = MAX_CONTENT_FILES,
) -> dict[str, str]:
    def _priority_score(path: str) -> int:
        normalized = path.lower()
        score = 0
        if normalized.startswith(".github/workflows/"):
            score += 90
        if normalized.startswith("infra/") or "/infra/" in normalized:
            score += 80
        if normalized.startswith("terraform/") or normalized.endswith(".tf"):
            score += 75
        if normalized.startswith("k8s/") or "/kubernetes/" in normalized:
            score += 70
        for idx, pat in enumerate(PRIORITY_FILE_PATTERNS):
            if normalized.endswith(pat):
                score += 100 - idx
                break
        return score

    candidates: list[tuple[int, str, str]] = []
    for item in tree_items:
        path = item.get("path")
        sha = item.get("sha")
        if not isinstance(path, str) or not isinstance(sha, str):
            continue
        normalized = path.lower()
        filename = normalized.split("/")[-1]
        is_workflow = normalized.startswith(".github/workflows/") and normalized.endswith((".yml", ".yaml"))
        if filename in INTERESTING_FILE_NAMES or is_workflow:
            candidates.append((_priority_score(normalized), normalized, sha))

    candidates.sort(key=lambda row: (-row[0], row[1]))
    selected = [(path, sha) for _, path, sha in candidates[:max_files]]

    contents: dict[str, str] = {}
    for path, sha in selected:
        blob = _github_request(f"/repos/{encoded_full_name}/git/blobs/{sha}", access_token=access_token)
        if not isinstance(blob, dict):
            continue
        decoded = _decode_blob_content(blob)
        if decoded:
            contents[path] = decoded[:MAX_SNIPPET_CHARS]
    return contents


def _detect_flags(files: list[str]) -> dict[str, bool]:
    lowered = [f.lower() for f in files]
    return {
        "dockerfile": any(path.endswith("dockerfile") for path in lowered),
        "k8sManifests": any(("k8s" in path or "/kubernetes/" in path) and path.endswith((".yaml", ".yml")) for path in lowered),
        "serverlessConfig": any(path.endswith(("serverless.yml", "serverless.yaml", "template.yml", "template.yaml")) for path in lowered),
        "terraform": any(path.endswith(".tf") for path in lowered),
        "cdk": any(path.endswith("cdk.json") for path in lowered),
        "githubActions": any(path.startswith(".github/workflows/") for path in lowered),
        "readme": any(path.endswith("readme.md") for path in lowered),
    }


def _extract_language_hints(files: list[str]) -> list[str]:
    lowered = {f.lower().split("/")[-1] for f in files}
    hints: list[str] = []
    if "package.json" in lowered:
        hints.append("Node.js/TypeScript")
    if "requirements.txt" in lowered or "pyproject.toml" in lowered:
        hints.append("Python")
    if "pom.xml" in lowered or "build.gradle" in lowered:
        hints.append("Java")
    if "go.mod" in lowered:
        hints.append("Go")
    if "cargo.toml" in lowered:
        hints.append("Rust")
    return hints


def _dependency_files(files: list[str]) -> list[str]:
    names = {
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "pom.xml",
        "build.gradle",
        "go.mod",
        "cargo.toml",
    }
    return [path for path in files if path.lower().split("/")[-1] in names][:20]


def _build_repo_prompt(
    *,
    full_name: str,
    default_branch: str,
    repo_meta: dict[str, Any],
    files: list[str],
    file_contents: dict[str, str],
) -> str:
    description = str(repo_meta.get("description") or "")
    topics = repo_meta.get("topics") if isinstance(repo_meta.get("topics"), list) else []
    topics_text = ", ".join(str(t) for t in topics[:10])
    file_list = "\n".join(f"- {path}" for path in files[:MAX_FILE_LIST_ITEMS])

    snippets = []
    for path, content in file_contents.items():
        snippets.append(f"[{path}]\n{content}")
    snippets_text = "\n\n".join(snippets)

    return (
        f"Repository: {full_name}\n"
        f"Default branch: {default_branch}\n"
        f"Description: {description}\n"
        f"Topics: {topics_text}\n\n"
        f"File tree sample:\n{file_list}\n\n"
        f"Important file snippets:\n{snippets_text}\n\n"
        "Task: Infer realistic AWS deployment architecture for this repository."
    )


def _required_services(architecture: dict[str, Any], recommended_stack: list[str]) -> list[str]:
    additional = [str(s) for s in architecture.get("additional_services", []) if str(s).strip()]
    return sorted(set(recommended_stack + ["AWS IAM", "Amazon CloudWatch"] + additional))


def _contains_keywords(texts: list[str], keywords: list[str]) -> bool:
    merged = "\n".join(texts).lower()
    return any(keyword in merged for keyword in keywords)


def _apply_repo_sanity_overrides(
    *,
    architecture: dict[str, Any],
    detected: dict[str, bool],
    file_contents: dict[str, str],
) -> dict[str, Any]:
    adjusted = dict(architecture)
    ec2 = dict(adjusted.get("ec2", {}) or {})
    rds = dict(adjusted.get("rds", {}) or {})
    additional = {str(s).lower() for s in adjusted.get("additional_services", []) if str(s).strip()}
    texts = [value for value in file_contents.values() if value]

    is_serverless_repo = detected.get("serverlessConfig", False) and not detected.get("dockerfile", False)
    is_container_repo = detected.get("dockerfile", False) and not detected.get("k8sManifests", False)
    db_signals = _contains_keywords(
        texts,
        ["postgres", "postgresql", "mysql", "database", "rds", "typeorm", "sqlalchemy", "prisma"],
    )

    if is_serverless_repo:
        ec2["count"] = 1
        ec2["instance_type"] = "t3.micro"
        additional.add("lambda")
        additional.add("apigateway")
        additional.discard("ecs")
        additional.discard("eks")
        if not db_signals:
            rds["enabled"] = False
            rds["engine"] = None

    if is_container_repo:
        additional.add("ecs")
        additional.add("alb")
        additional.discard("eks")
        ec2["count"] = max(1, int(ec2.get("count", 1)))

    adjusted["ec2"] = {
        "count": max(1, min(10, int(ec2.get("count", 1)))),
        "instance_type": str(ec2.get("instance_type", "t3.micro")),
    }
    adjusted["rds"] = {
        "enabled": bool(rds.get("enabled", False)),
        "engine": rds.get("engine") if bool(rds.get("enabled", False)) else None,
    }
    adjusted["additional_services"] = sorted(additional)
    return adjusted


def _normalize_recommended_stack(
    *,
    raw_stack: list[str],
    detected: dict[str, bool],
    architecture: dict[str, Any],
    files: list[str] | None = None,
) -> list[str]:
    lowered_files = {str(f).lower() for f in (files or [])}
    is_static_site = (
        ("index.html" in lowered_files or "public/index.html" in lowered_files)
        and not detected.get("dockerfile", False)
        and not detected.get("serverlessConfig", False)
        and not detected.get("k8sManifests", False)
    )
    if is_static_site:
        return ["Amazon S3", "Amazon CloudFront", "AWS Amplify Hosting"]

    normalized: list[str] = []
    joined_raw = " ".join(raw_stack).lower()

    if "eks" in joined_raw:
        normalized.append("Amazon EKS")
    if "ecs" in joined_raw or "fargate" in joined_raw:
        normalized.append("Amazon ECS (Fargate)")
    if "lambda" in joined_raw:
        normalized.append("AWS Lambda")
    if "api gateway" in joined_raw or "apigateway" in joined_raw:
        normalized.append("Amazon API Gateway")
    if "ec2" in joined_raw:
        normalized.append("Amazon EC2")
    if "s3" in joined_raw:
        normalized.append("Amazon S3")
    if "cloudfront" in joined_raw:
        normalized.append("Amazon CloudFront")
    if "amplify" in joined_raw:
        normalized.append("AWS Amplify Hosting")
    if "rds" in joined_raw or "database" in joined_raw:
        normalized.append("Amazon RDS")
    if "alb" in joined_raw or "load balancer" in joined_raw:
        normalized.append("Application Load Balancer")

    if not normalized:
        services = {str(s).lower() for s in architecture.get("additional_services", [])}
        if "eks" in services:
            normalized = ["Amazon EKS", "Amazon ECR", "Application Load Balancer"]
        elif "ecs" in services or detected.get("dockerfile", False):
            normalized = ["Amazon ECS (Fargate)", "Amazon ECR", "Application Load Balancer"]
        elif "lambda" in services or detected.get("serverlessConfig", False):
            normalized = ["AWS Lambda", "Amazon API Gateway", "Amazon CloudWatch"]
        else:
            normalized = ["Amazon EC2"]

    return list(dict.fromkeys(normalized))


def _stack_consistency_issues(architecture: dict[str, Any], recommended_stack: list[str]) -> list[str]:
    issues: list[str] = []
    stack_text = " ".join(recommended_stack).lower()
    services = {str(s).lower() for s in architecture.get("additional_services", [])}
    ec2_count = int((architecture.get("ec2", {}) or {}).get("count", 1))

    if ec2_count == 0 and "ec2" in stack_text:
        issues.append("아키텍처의 EC2 count가 0인데 추천 스택에 EC2가 포함되어 있습니다.")
    if "lambda" in services and "lambda" not in stack_text:
        issues.append("아키텍처에 Lambda가 포함됐는데 추천 스택 설명에 Lambda가 없습니다.")
    if "eks" in services and "eks" not in stack_text:
        issues.append("아키텍처에 EKS가 포함됐는데 추천 스택 설명에 EKS가 없습니다.")
    if "ecs" in services and "ecs" not in stack_text:
        issues.append("아키텍처에 ECS가 포함됐는데 추천 스택 설명에 ECS가 없습니다.")
    if "rds" in services and "rds" not in stack_text and "database" not in stack_text:
        issues.append("아키텍처에 RDS가 포함됐는데 추천 스택/설명에 DB가 명시되지 않았습니다.")
    return issues[:4]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _contains_hangul(text: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


def _report_needs_korean_retry(report: dict[str, Any]) -> bool:
    texts: list[str] = []
    texts.append(str(report.get("summary", "")))
    texts.extend(str(v) for v in report.get("findings", []) if str(v).strip())
    texts.extend(str(v) for v in report.get("deploymentSteps", []) if str(v).strip())
    joined = "\n".join(texts).strip()
    if not joined:
        return False
    return not _contains_hangul(joined)


def _ensure_repo_analysis_ai_ready() -> None:
    if not REPO_ANALYSIS_AI_ONLY:
        return
    if os.getenv("BEDROCK_ENABLED", "true").lower() != "true":
        raise HTTPException(
            status_code=503,
            detail="레포 분석은 AI 전용 모드입니다. `BEDROCK_ENABLED=true`로 설정해 주세요.",
        )
    if os.getenv("BEDROCK_STRICT_MODE", "false").lower() != "true":
        raise HTTPException(
            status_code=503,
            detail="레포 분석은 AI 전용 모드입니다. `BEDROCK_STRICT_MODE=true`로 설정해 주세요.",
        )
    if os.getenv("BEDROCK_FALLBACK_ENABLED", "true").lower() == "true":
        raise HTTPException(
            status_code=503,
            detail="레포 분석은 AI 전용 모드입니다. `BEDROCK_FALLBACK_ENABLED=false`로 설정해 주세요.",
        )


def _build_confidence(
    *,
    analysis_meta: dict[str, Any] | None,
    detected_flags: dict[str, bool],
    evidence_files: list[str],
) -> tuple[float, str, str, bool]:
    meta = analysis_meta or {}
    provider = str(meta.get("provider") or "unknown")
    fallback_used = bool(meta.get("fallbackUsed", False))
    coverage_raw = meta.get("requirementCoverage")
    coverage = float(coverage_raw) if isinstance(coverage_raw, (int, float)) else 0.65
    coverage = _clamp(coverage, 0.0, 1.0)

    evidence_factor = _clamp(len(evidence_files) / 8.0, 0.0, 1.0)
    flag_count = sum(1 for value in detected_flags.values() if value)
    signal_factor = _clamp(flag_count / 7.0, 0.0, 1.0)
    provider_bonus = 0.08 if provider == "bedrock" and not fallback_used else (-0.05 if fallback_used else 0.0)

    score = 0.35 + (0.35 * coverage) + (0.2 * evidence_factor) + (0.1 * signal_factor) + provider_bonus
    score = round(_clamp(score, 0.0, 1.0), 3)
    if score >= 0.8:
        label = CONFIDENCE_LABEL_HIGH
    elif score >= 0.6:
        label = CONFIDENCE_LABEL_MEDIUM
    else:
        label = CONFIDENCE_LABEL_LOW
    return score, label, provider, fallback_used


def _confidence_extras(
    *,
    confidence_score: float,
    evidence_files: list[str],
    fallback_used: bool,
    detected_flags: dict[str, bool],
) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    improvements: list[str] = []

    if confidence_score >= 0.8:
        reasons.append("레포 핵심 파일이 충분히 수집되어 분석 근거가 비교적 많습니다.")
    elif confidence_score >= 0.6:
        reasons.append("핵심 파일 일부만 반영되어 분석 정확도가 중간 수준입니다.")
    else:
        reasons.append("수집된 근거 파일이 부족하거나 모델 폴백이 발생해 신뢰도가 낮습니다.")

    if len(evidence_files) >= 8:
        reasons.append("README/워크플로우/의존성 파일 등 다양한 신호를 사용했습니다.")
    elif len(evidence_files) >= 4:
        reasons.append("기본 설정 파일 위주로 분석했습니다.")
    else:
        reasons.append("파일 수집량이 적어 추정 오차가 커질 수 있습니다.")

    if fallback_used:
        reasons.append("AI 호출 폴백 모드가 사용되어 결과가 보수적으로 생성되었습니다.")

    if not detected_flags.get("readme", False):
        improvements.append("README에 배포 대상(정적 웹/API/배치), 데이터베이스 사용 여부를 명시하세요.")
    if not detected_flags.get("githubActions", False):
        improvements.append("`.github/workflows`에 테스트/빌드 워크플로우를 추가하세요.")
    improvements.append("프로덕션 배포 의도를 반영한 파일(Dockerfile, IaC, env 예시)을 레포에 포함하세요.")
    if confidence_score < 0.7:
        improvements.append("분석 모드를 deep으로 실행해 더 많은 파일 기반으로 다시 분석하세요.")
    return reasons[:4], improvements[:4]


def _run_ai_analysis(
    *,
    full_name: str,
    default_branch: str,
    repo_meta: dict[str, Any],
    files: list[str],
    file_contents: dict[str, str],
    consistency_feedback: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], float, str, str, bool, list[str]]:
    repo_prompt = _build_repo_prompt(
        full_name=full_name,
        default_branch=default_branch,
        repo_meta=repo_meta,
        files=files,
        file_contents=file_contents,
    )
    architecture, analysis_meta = parse_architecture_with_retry(repo_prompt, ARCH_SCHEMA)
    report, report_meta = generate_repo_report_with_ai(
        repo_prompt=repo_prompt,
        architecture=architecture,
        model_rationale=analysis_meta.get("rationale") if isinstance(analysis_meta, dict) else None,
        consistency_feedback=consistency_feedback,
    )
    detected = _detect_flags(files)
    evidence_files = list(file_contents.keys())[:10]
    combined_meta = dict(analysis_meta if isinstance(analysis_meta, dict) else {})
    if isinstance(report_meta, dict):
        if report_meta.get("provider"):
            combined_meta["provider"] = report_meta.get("provider")
        combined_meta["fallbackUsed"] = bool(report_meta.get("fallbackUsed", combined_meta.get("fallbackUsed", False)))
        if report_meta.get("reason"):
            combined_meta["reportReason"] = report_meta.get("reason")

    confidence_score, confidence_label, analysis_provider, fallback_used = _build_confidence(
        analysis_meta=combined_meta,
        detected_flags=detected,
        evidence_files=evidence_files,
    )
    return (
        architecture,
        combined_meta,
        report,
        confidence_score,
        confidence_label,
        analysis_provider,
        fallback_used,
        evidence_files,
    )


def _cache_key(*, full_name: str, default_branch: str, mode: str, files: list[str]) -> str:
    joined = "\n".join(sorted(files)[:2000])
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
    return f"{full_name}:{default_branch}:{mode}:{digest}"


@router.get("/api/github/repos", response_model=GitHubRepoListResponse)
def list_github_repos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GitHubRepoListResponse:
    token = _require_github_token(db, current_user)
    response = _github_request(
        "/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member",
        access_token=token,
    )
    if not isinstance(response, list):
        raise HTTPException(status_code=502, detail="GitHub 레포 목록 응답 형식이 올바르지 않습니다.")

    repos: list[GitHubRepoItem] = []
    for item in response:
        if not isinstance(item, dict):
            continue
        owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
        repos.append(
            GitHubRepoItem(
                fullName=str(item.get("full_name", "")),
                name=str(item.get("name", "")),
                owner=str(owner.get("login", "")),
                private=bool(item.get("private", False)),
                defaultBranch=str(item.get("default_branch", "main")),
                htmlUrl=str(item.get("html_url", "")),
                updatedAt=str(item.get("updated_at", "")),
            )
        )
    repos.sort(key=lambda repo: repo.updatedAt, reverse=True)
    return GitHubRepoListResponse(repos=repos)


@router.get("/api/github/status", response_model=GitHubConnectionStatusResponse)
def github_connection_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GitHubConnectionStatusResponse:
    oauth_configured = _github_oauth_configured()
    token = get_github_access_token(db, current_user.id)
    token_present = bool(token)
    token_valid = False
    github_api_reachable = False
    account_login: str | None = None
    private_repo_access = False
    estimated_repo_count: int | None = None
    issues: list[str] = []

    if not oauth_configured:
        issues.append("GitHub OAuth 설정이 비어 있습니다. .env의 GITHUB_OAUTH_CLIENT_ID/SECRET를 확인하세요.")
    if not token_present:
        issues.append("저장된 GitHub 토큰이 없습니다. GitHub 소셜 로그인을 다시 진행하세요.")

    if token_present and token:
        try:
            profile = _github_request("/user", access_token=token)
            github_api_reachable = True
            token_valid = True
            if isinstance(profile, dict):
                account_login = str(profile.get("login", "") or "") or None

            repos = _github_request("/user/repos?per_page=10&sort=updated", access_token=token)
            if isinstance(repos, list):
                estimated_repo_count = len(repos)
                private_repo_access = any(bool(item.get("private", False)) for item in repos if isinstance(item, dict))
        except HTTPException as exc:
            if exc.status_code in {401, 403}:
                issues.append("토큰이 만료되었거나 권한이 부족합니다. GitHub 로그인과 조직 권한 승인 상태를 확인하세요.")
            else:
                issues.append(f"GitHub API 상태 확인 실패: {exc.detail}")

    return GitHubConnectionStatusResponse(
        oauthConfigured=oauth_configured,
        tokenPresent=token_present,
        tokenValid=token_valid,
        githubApiReachable=github_api_reachable,
        accountLogin=account_login,
        privateRepoAccess=private_repo_access,
        estimatedRepoCount=estimated_repo_count,
        issues=issues,
    )


@router.post("/api/github/repo-analysis", response_model=GitHubRepoAnalyzeResponse)
def analyze_github_repo(
    payload: GitHubRepoAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GitHubRepoAnalyzeResponse:
    _ensure_repo_analysis_ai_ready()
    token = _require_github_token(db, current_user)
    full_name = _validate_repo_full_name(payload.fullName)
    encoded_full_name = urllib.parse.quote(full_name, safe="/")

    repo_meta = _github_request(f"/repos/{encoded_full_name}", access_token=token)
    if not isinstance(repo_meta, dict):
        raise HTTPException(status_code=502, detail="GitHub 레포 메타 응답 형식이 올바르지 않습니다.")
    default_branch = str(repo_meta.get("default_branch", "main"))

    tree_response = _github_request(
        f"/repos/{encoded_full_name}/git/trees/{urllib.parse.quote(default_branch, safe='')}?recursive=1",
        access_token=token,
    )
    if not isinstance(tree_response, dict):
        raise HTTPException(status_code=502, detail="GitHub 파일 트리 응답 형식이 올바르지 않습니다.")
    raw_tree_items = tree_response.get("tree")
    if not isinstance(raw_tree_items, list):
        raise HTTPException(status_code=502, detail="GitHub 파일 트리 데이터가 없습니다.")

    tree_items = [item for item in raw_tree_items if isinstance(item, dict)]
    files = [
        str(item.get("path"))
        for item in tree_items
        if item.get("type") == "blob" and isinstance(item.get("path"), str)
    ]
    mode = "deep"
    force_refresh = bool(payload.forceRefresh)
    cache_key = _cache_key(full_name=full_name, default_branch=default_branch, mode=mode, files=files)
    cached = get_cached_analysis(cache_key)
    if cached and not force_refresh:
        return GitHubRepoAnalyzeResponse(**(cached | {"cacheHit": True}))

    initial_max_files = MAX_CONTENT_FILES_DEEP if mode == "deep" else MAX_CONTENT_FILES
    file_contents = _collect_file_contents(
        encoded_full_name=encoded_full_name,
        access_token=token,
        tree_items=tree_items,
        max_files=initial_max_files,
    )

    try:
        (
            architecture,
            analysis_meta,
            report,
            confidence_score,
            confidence_label,
            analysis_provider,
            fallback_used,
            evidence_files,
            ) = _run_ai_analysis(
                full_name=full_name,
                default_branch=default_branch,
                repo_meta=repo_meta,
                files=files,
            file_contents=file_contents,
        )
    except AIParseError as exc:
        log_repo_analysis_failure(
            {
                "stage": "primary_ai_analysis",
                "error_type": "AIParseError",
                "error_code": exc.code,
                "error_message": exc.message,
                "repo": full_name,
                "mode": mode,
                "default_branch": default_branch,
                "file_count": len(files),
                "sample_files": files[:30],
            }
        )
        raise HTTPException(
            status_code=502,
            detail=f"AI 분석(Bedrock) 실패: {exc.code} - {exc.message}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        log_repo_analysis_failure(
            {
                "stage": "primary_ai_analysis",
                "error_type": "Exception",
                "error_message": str(exc),
                "repo": full_name,
                "mode": mode,
                "default_branch": default_branch,
                "file_count": len(files),
                "sample_files": files[:30],
            }
        )
        raise HTTPException(
            status_code=502,
            detail=f"AI 분석(Bedrock) 실패: {exc}",
        ) from exc

    detected = _detect_flags(files)
    architecture = _apply_repo_sanity_overrides(
        architecture=architecture,
        detected=detected,
        file_contents=file_contents,
    )

    retry_threshold = CONFIDENCE_RETRY_THRESHOLD if mode == "fast" else 0.85
    if confidence_score < retry_threshold:
        retry_file_contents = _collect_file_contents(
            encoded_full_name=encoded_full_name,
            access_token=token,
            tree_items=tree_items,
            max_files=MAX_CONTENT_FILES_DEEP if mode == "deep" else MAX_CONTENT_FILES_RETRY,
        )
        if len(retry_file_contents) > len(file_contents):
            try:
                (
                    architecture_retry,
                    analysis_meta_retry,
                    report_retry,
                    confidence_score_retry,
                    confidence_label_retry,
                    analysis_provider_retry,
                    fallback_used_retry,
                    evidence_files_retry,
                ) = _run_ai_analysis(
                    full_name=full_name,
                    default_branch=default_branch,
                    repo_meta=repo_meta,
                    files=files,
                    file_contents=retry_file_contents,
                )
            except Exception:
                log_repo_analysis_failure(
                    {
                        "stage": "retry_ai_analysis",
                        "error_type": "Exception",
                        "error_message": "retry analysis failed; kept previous result",
                        "repo": full_name,
                        "mode": mode,
                        "default_branch": default_branch,
                        "file_count": len(files),
                        "sample_files": files[:30],
                    }
                )
                architecture_retry = architecture
                analysis_meta_retry = analysis_meta
                report_retry = report
                confidence_score_retry = confidence_score
                confidence_label_retry = confidence_label
                analysis_provider_retry = analysis_provider
                fallback_used_retry = fallback_used
                evidence_files_retry = evidence_files
            if confidence_score_retry >= confidence_score:
                architecture = architecture_retry
                analysis_meta = analysis_meta_retry
                report = report_retry
                confidence_score = confidence_score_retry
                confidence_label = confidence_label_retry
                analysis_provider = analysis_provider_retry
                fallback_used = fallback_used_retry
                evidence_files = evidence_files_retry
                architecture = _apply_repo_sanity_overrides(
                    architecture=architecture,
                    detected=detected,
                    file_contents=retry_file_contents,
                )

    if _report_needs_korean_retry(report):
        try:
            (
                architecture_ko,
                analysis_meta_ko,
                report_ko,
                confidence_score_ko,
                confidence_label_ko,
                analysis_provider_ko,
                fallback_used_ko,
                evidence_files_ko,
            ) = _run_ai_analysis(
                full_name=full_name,
                default_branch=default_branch,
                repo_meta=repo_meta,
                files=files,
                file_contents=file_contents,
                consistency_feedback=["출력 텍스트를 반드시 한국어로 작성하세요. 영어 문장은 사용하지 마세요."],
            )
            if not _report_needs_korean_retry(report_ko):
                architecture = architecture_ko
                analysis_meta = analysis_meta_ko
                report = report_ko
                confidence_score = confidence_score_ko
                confidence_label = confidence_label_ko
                analysis_provider = analysis_provider_ko
                fallback_used = fallback_used_ko
                evidence_files = evidence_files_ko
        except Exception:
            log_repo_analysis_failure(
                {
                    "stage": "korean_retry",
                    "error_type": "Exception",
                    "error_message": "korean retry failed; kept previous report",
                    "repo": full_name,
                    "mode": mode,
                    "default_branch": default_branch,
                    "file_count": len(files),
                    "sample_files": files[:30],
                }
            )

    terraform_code = generate_terraform_from_architecture(architecture)
    cost = estimate_monthly_cost(architecture)
    recommended_stack_raw = [str(v) for v in report.get("recommendedStack", []) if str(v).strip()]
    recommended_stack = _normalize_recommended_stack(
        raw_stack=recommended_stack_raw,
        detected=detected,
        architecture=architecture,
        files=files,
    )
    if not recommended_stack:
        recommended_stack = ["Amazon EC2"]
    consistency_issues = _stack_consistency_issues(architecture, recommended_stack)
    if consistency_issues:
        try:
            (
                architecture_fix,
                analysis_meta_fix,
                report_fix,
                confidence_score_fix,
                confidence_label_fix,
                analysis_provider_fix,
                fallback_used_fix,
                evidence_files_fix,
            ) = _run_ai_analysis(
                full_name=full_name,
                default_branch=default_branch,
                repo_meta=repo_meta,
                files=files,
                file_contents=file_contents,
                consistency_feedback=consistency_issues,
            )
            recommended_stack_fix = [str(v) for v in report_fix.get("recommendedStack", []) if str(v).strip()]
            if recommended_stack_fix:
                architecture = architecture_fix
                analysis_meta = analysis_meta_fix
                report = report_fix
                confidence_score = confidence_score_fix
                confidence_label = confidence_label_fix
                analysis_provider = analysis_provider_fix
                fallback_used = fallback_used_fix
                evidence_files = evidence_files_fix
                recommended_stack = recommended_stack_fix
        except Exception:
            log_repo_analysis_failure(
                {
                    "stage": "consistency_fix",
                    "error_type": "Exception",
                    "error_message": "consistency fix retry failed; kept previous report",
                    "repo": full_name,
                    "mode": mode,
                    "default_branch": default_branch,
                    "file_count": len(files),
                    "sample_files": files[:30],
                }
            )
            pass
    if REPO_ANALYSIS_AI_ONLY and (analysis_provider != "bedrock" or fallback_used):
        raise HTTPException(
            status_code=502,
            detail="AI 전용 분석 정책 위반: Bedrock 분석에 실패했습니다. AWS/Bedrock 설정을 점검해 주세요.",
        )
    confidence_reasons, improvement_actions = _confidence_extras(
        confidence_score=confidence_score,
        evidence_files=evidence_files,
        fallback_used=fallback_used,
        detected_flags=detected,
    )
    response_payload = {
        "fullName": full_name,
        "defaultBranch": default_branch,
        "scannedFileCount": len(files),
        "summary": str(report.get("summary", "")),
        "findings": [str(v) for v in report.get("findings", []) if str(v).strip()],
        "recommendedStack": recommended_stack,
        "requiredServices": _required_services(architecture, recommended_stack),
        "languageHints": _extract_language_hints(files),
        "dependencyFiles": _dependency_files(files),
        "deploymentSteps": [str(v) for v in report.get("deploymentSteps", []) if str(v).strip()],
        "risks": [str(v) for v in report.get("risks", []) if str(v).strip()],
        "costNotes": [str(v) for v in report.get("costNotes", []) if str(v).strip()],
        "detected": detected,
        "architectureJson": architecture,
        "terraformCode": terraform_code,
        "cost": cost,
        "confidenceScore": confidence_score,
        "confidenceLabel": confidence_label,
        "evidenceFiles": evidence_files,
        "analysisProvider": analysis_provider,
        "fallbackUsed": fallback_used,
        "analysisMode": mode,
        "cacheHit": False,
        "confidenceReasons": confidence_reasons,
        "improvementActions": improvement_actions,
    }
    put_cached_analysis(cache_key, response_payload)
    return GitHubRepoAnalyzeResponse(**response_payload)
