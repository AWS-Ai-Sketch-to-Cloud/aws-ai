from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import dt_to_iso
from app.core.deps import get_current_user
from app.database import get_db
from app.models import AppSession, Project, User
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectListItem,
    ProjectListResponse,
)
from app.schemas.session import SessionCreateApiRequest, SessionCreateApiResponse, SessionListItem, SessionListResponse
from app.services.session_service import record_session_event

router = APIRouter()


@router.post("/api/projects", response_model=ProjectCreateResponse)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectCreateResponse:
    project = Project(name=payload.name, description=payload.description, owner_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectCreateResponse(
        projectId=str(project.id),
        name=project.name,
        description=project.description,
        ownerId=str(project.owner_id) if project.owner_id else None,
        createdAt=dt_to_iso(project.created_at),
    )


@router.get("/api/projects", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectListResponse:
    rows = db.scalars(
        select(Project).where(Project.owner_id == current_user.id).order_by(Project.created_at.desc())
    ).all()
    return ProjectListResponse(
        items=[
            ProjectListItem(
                projectId=str(p.id),
                name=p.name,
                description=p.description,
                createdAt=dt_to_iso(p.created_at),
                updatedAt=dt_to_iso(p.updated_at),
            )
            for p in rows
        ]
    )


@router.post("/api/projects/{project_id}/sessions", response_model=SessionCreateApiResponse)
def create_project_session(
    project_id: str,
    payload: SessionCreateApiRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionCreateApiResponse:
    try:
        pid = UUID(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid project id") from e

    project = db.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="forbidden")

    latest = db.scalars(
        select(AppSession).where(AppSession.project_id == pid).order_by(AppSession.version_no.desc()).limit(1)
    ).first()
    next_version = 1 if not latest else latest.version_no + 1

    session = AppSession(
        project_id=pid,
        version_no=next_version,
        input_type=payload.inputType,
        input_text=payload.inputText,
        input_image_url=payload.inputImageUrl,
        status="CREATED",
    )
    db.add(session)
    db.flush()
    record_session_event(
        db,
        session,
        "SESSION_CREATED",
        {
            "projectId": str(project.id),
            "versionNo": next_version,
            "inputType": payload.inputType,
        },
    )
    db.commit()
    db.refresh(session)
    return SessionCreateApiResponse(
        sessionId=str(session.id),
        projectId=str(session.project_id),
        versionNo=session.version_no,
        status=session.status,
        createdAt=dt_to_iso(session.created_at),
    )


@router.get("/api/projects/{project_id}/sessions", response_model=SessionListResponse)
def list_project_sessions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionListResponse:
    try:
        pid = UUID(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid project id") from e

    project = db.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="forbidden")

    rows = db.scalars(
        select(AppSession).where(AppSession.project_id == pid).order_by(AppSession.version_no.desc())
    ).all()
    return SessionListResponse(
        items=[
            SessionListItem(
                sessionId=str(s.id),
                versionNo=s.version_no,
                inputType=s.input_type,
                status=s.status,
                createdAt=dt_to_iso(s.created_at),
                updatedAt=dt_to_iso(s.updated_at),
            )
            for s in rows
        ]
    )
