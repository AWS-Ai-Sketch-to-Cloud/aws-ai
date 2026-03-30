from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.cost_calculator import estimate_monthly_cost
from app.database import get_db
from app.models import User
from app.schemas.github import (
    GitHubRepoAnalyzeRequest,
    GitHubRepoAnalyzeResponse,
    GitHubRepoItem,
    GitHubRepoListResponse,
)
from app.services.github_oauth_store import get_github_access_token
from app.services.github_repo_analysis import build_repo_analysis
from app.terraform_generator import generate_terraform_from_architecture

router = APIRouter()

MAX_CONTENT_FILES = 10
MAX_CONTENT_BYTES = 80_000
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
}


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
    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _collect_file_contents(
    *,
    encoded_full_name: str,
    access_token: str,
    tree_items: list[dict[str, Any]],
) -> dict[str, str]:
    selected: list[tuple[str, str]] = []
    for item in tree_items:
        path = item.get("path")
        sha = item.get("sha")
        if not isinstance(path, str) or not isinstance(sha, str):
            continue
        normalized = path.lower()
        filename = normalized.split("/")[-1]
        is_workflow = normalized.startswith(".github/workflows/") and normalized.endswith((".yml", ".yaml"))
        if filename in INTERESTING_FILE_NAMES or is_workflow:
            selected.append((normalized, sha))
        if len(selected) >= MAX_CONTENT_FILES:
            break

    contents: dict[str, str] = {}
    for path, sha in selected:
        blob = _github_request(f"/repos/{encoded_full_name}/git/blobs/{sha}", access_token=access_token)
        if not isinstance(blob, dict):
            continue
        contents[path] = _decode_blob_content(blob)
    return contents


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


@router.post("/api/github/repo-analysis", response_model=GitHubRepoAnalyzeResponse)
def analyze_github_repo(
    payload: GitHubRepoAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GitHubRepoAnalyzeResponse:
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
    file_contents = _collect_file_contents(
        encoded_full_name=encoded_full_name,
        access_token=token,
        tree_items=tree_items,
    )

    analysis = build_repo_analysis(
        full_name=full_name,
        default_branch=default_branch,
        files=files,
        file_contents=file_contents,
    )
    architecture = dict(analysis["architecture"])
    terraform_code = generate_terraform_from_architecture(architecture)
    cost = estimate_monthly_cost(architecture)

    return GitHubRepoAnalyzeResponse(
        fullName=full_name,
        defaultBranch=default_branch,
        scannedFileCount=len(files),
        summary=str(analysis["summary"]),
        findings=[str(value) for value in analysis["findings"]],
        recommendedStack=[str(value) for value in analysis["recommendedStack"]],
        requiredServices=[str(value) for value in analysis["requiredServices"]],
        languageHints=[str(value) for value in analysis["languageHints"]],
        dependencyFiles=[str(value) for value in analysis["dependencyFiles"]],
        deploymentSteps=[str(value) for value in analysis["deploymentSteps"]],
        risks=[str(value) for value in analysis["risks"]],
        costNotes=[str(value) for value in analysis["costNotes"]],
        detected={str(key): bool(value) for key, value in dict(analysis["detected"]).items()},
        architectureJson=architecture,
        terraformCode=terraform_code,
        cost=cost,
    )
