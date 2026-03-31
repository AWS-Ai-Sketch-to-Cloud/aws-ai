from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models import User
from app.services.analysis_failure_logger import (
    append_repo_analysis_feedback,
    read_latest_repo_analysis_feedback,
    summarize_repo_analysis_failures,
)
from app.services.github_analysis_cache import get_cache_stats

router = APIRouter()


def _bool_env(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() == "true"


class RepoAnalysisFeedbackRequest(BaseModel):
    fullName: str = Field(min_length=3, max_length=200)
    verdict: str = Field(pattern="^(APPROVE|HOLD)$")
    note: str | None = Field(default=None, max_length=300)


def _readiness_score(*, policy_ready: bool, failure_total: int, cache_hits: int, cache_misses: int) -> int:
    score = 100
    if not policy_ready:
        score -= 40
    score -= min(30, failure_total * 3)
    total_cache = cache_hits + cache_misses
    if total_cache >= 5:
        hit_rate = cache_hits / total_cache
        if hit_rate < 0.2:
            score -= 10
        elif hit_rate < 0.4:
            score -= 5
    return max(0, min(100, score))


@router.get("/api/ops/repo-analysis-health")
def repo_analysis_health(
    current_user: User = Depends(get_current_user),
) -> dict:
    del current_user

    bedrock_enabled = _bool_env("BEDROCK_ENABLED", "true")
    bedrock_strict = _bool_env("BEDROCK_STRICT_MODE", "false")
    fallback_enabled = _bool_env("BEDROCK_FALLBACK_ENABLED", "true")
    ai_only = _bool_env("GITHUB_REPO_ANALYSIS_AI_ONLY", "true")

    policy_ready = bedrock_enabled and bedrock_strict and (not fallback_enabled)
    failures = summarize_repo_analysis_failures(limit=100)
    recommendations: list[str] = []

    if ai_only and not policy_ready:
        recommendations.append("AI 전용 정책 설정이 맞지 않습니다. 서버 설정을 확인해 주세요.")
    if failures["total"] > 0:
        recommendations.append("최근 분석 실패가 있습니다. 잠시 후 다시 시도해 주세요.")
    if failures["byType"].get("AIParseError", 0) >= 3:
        recommendations.append("분석 입력이 부족할 수 있습니다. README, 배포 파일, 워크플로우 파일을 추가해 보세요.")

    return {
        "policy": {
            "aiOnly": ai_only,
            "bedrockEnabled": bedrock_enabled,
            "bedrockStrictMode": bedrock_strict,
            "bedrockFallbackEnabled": fallback_enabled,
            "ready": (policy_ready if ai_only else bedrock_enabled),
        },
        "cache": get_cache_stats(),
        "failures": failures,
        "recommendations": recommendations,
    }


@router.get("/api/ops/readiness")
def repo_analysis_readiness(
    current_user: User = Depends(get_current_user),
) -> dict:
    del current_user

    bedrock_enabled = _bool_env("BEDROCK_ENABLED", "true")
    bedrock_strict = _bool_env("BEDROCK_STRICT_MODE", "false")
    fallback_enabled = _bool_env("BEDROCK_FALLBACK_ENABLED", "true")
    ai_only = _bool_env("GITHUB_REPO_ANALYSIS_AI_ONLY", "true")
    policy_ready = bedrock_enabled and bedrock_strict and (not fallback_enabled)

    cache = get_cache_stats()
    failures = summarize_repo_analysis_failures(limit=200)
    score = _readiness_score(
        policy_ready=(policy_ready if ai_only else bedrock_enabled),
        failure_total=int(failures.get("total", 0)),
        cache_hits=int(cache.get("hits", 0)),
        cache_misses=int(cache.get("misses", 0)),
    )

    checklist = [
        {
            "name": "AI 분석 설정",
            "ok": (policy_ready if ai_only else bedrock_enabled),
            "detail": "AI 분석 관련 환경변수 설정 상태",
        },
        {
            "name": "최근 실패 건수",
            "ok": int(failures.get("total", 0)) < 5,
            "detail": f"최근 실패 {int(failures.get('total', 0))}건",
        },
        {
            "name": "캐시 동작",
            "ok": int(cache.get("size", 0)) >= 0,
            "detail": f"hits={cache.get('hits', 0)}, misses={cache.get('misses', 0)}",
        },
    ]
    return {
        "score": score,
        "grade": ("A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"),
        "checklist": checklist,
        "cache": cache,
        "failures": failures,
    }


@router.post("/api/ops/repo-analysis-feedback")
def save_repo_analysis_feedback(
    payload: RepoAnalysisFeedbackRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    append_repo_analysis_feedback(
        {
            "userId": str(current_user.id),
            "fullName": payload.fullName.strip(),
            "verdict": payload.verdict,
            "note": payload.note.strip() if isinstance(payload.note, str) and payload.note.strip() else None,
        }
    )
    return {
        "fullName": payload.fullName.strip(),
        "verdict": payload.verdict,
        "note": payload.note,
        "saved": True,
    }


@router.get("/api/ops/repo-analysis-feedback")
def get_repo_analysis_feedback(
    fullName: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    latest = read_latest_repo_analysis_feedback(user_id=str(current_user.id), full_name=fullName.strip())
    return {
        "fullName": fullName.strip(),
        "feedback": latest,
    }
