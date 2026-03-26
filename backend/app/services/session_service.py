from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSession, SessionEvent, User

SESSION_TRANSITIONS: dict[str, set[str]] = {
    "CREATED": {"ANALYZING", "ANALYZED", "FAILED"},
    "ANALYZING": {"ANALYZED", "FAILED"},
    "ANALYZED": {"GENERATING_TERRAFORM", "COST_CALCULATED", "FAILED"},
    "GENERATING_TERRAFORM": {"GENERATED", "FAILED"},
    "GENERATED": {"COST_CALCULATED", "FAILED"},
    "COST_CALCULATED": {"FAILED"},
    "FAILED": {"ANALYZING", "ANALYZED", "GENERATING_TERRAFORM"},
}


def record_session_event(
    db: Session, session: AppSession, event_type: str, payload: dict[str, Any] | None = None
) -> None:
    db.add(SessionEvent(session_id=session.id, event_type=event_type, payload_json=payload))


def transition_session_status(
    db: Session,
    session: AppSession,
    next_status: str,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    current_status = session.status
    allowed = SESSION_TRANSITIONS.get(current_status, set())
    if current_status != next_status and next_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"invalid status transition: {current_status} -> {next_status}",
        )

    session.status = next_status
    session.error_code = error_code
    session.error_message = error_message
    session.updated_at = datetime.now(timezone.utc)
    record_session_event(
        db,
        session,
        "STATUS_CHANGED",
        {
            "from": current_status,
            "to": next_status,
            "errorCode": error_code,
        },
    )


def get_session_or_404(db: Session, session_id: str) -> AppSession:
    try:
        sid = UUID(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid session id") from e

    session = db.get(AppSession, sid)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return session


def ensure_session_access(session: AppSession, current_user: User) -> None:
    if session.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="forbidden")


def get_compare_base_session(
    db: Session,
    target_session: AppSession,
    base_session_id: str | None,
) -> AppSession:
    if base_session_id:
        base_session = get_session_or_404(db, base_session_id)
        if base_session.project_id != target_session.project_id:
            raise HTTPException(status_code=400, detail="base session must belong to the same project")
        if base_session.id == target_session.id:
            raise HTTPException(status_code=400, detail="base session must be different from target session")
        return base_session

    previous_session = db.scalars(
        select(AppSession)
        .where(
            AppSession.project_id == target_session.project_id,
            AppSession.version_no < target_session.version_no,
        )
        .order_by(AppSession.version_no.desc())
        .limit(1)
    ).first()
    if not previous_session:
        raise HTTPException(status_code=404, detail="previous session not found for comparison")
    return previous_session
