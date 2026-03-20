from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from jsonschema import ValidationError, validate
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_parser import AIParseError, parse_architecture_with_retry
from app.cost_calculator import estimate_monthly_cost
from app.database import get_db
from app.models import AppSession, Project, SessionArchitecture, SessionCostResult, SessionTerraformResult
from app.terraform_generator import generate_terraform_from_architecture
from app.terraform_validator import validate_terraform_code

CONTRACT_VERSION = "v1"
ROOT = Path(__file__).resolve().parents[1]
ARCH_SCHEMA_PATH = ROOT / "A_JSON_스키마_v1.json"

with ARCH_SCHEMA_PATH.open("r", encoding="utf-8") as f:
    ARCH_SCHEMA = json.load(f)


def dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class ProjectCreateResponse(BaseModel):
    projectId: str
    name: str


class ProjectListItem(BaseModel):
    projectId: str
    name: str
    description: str | None = None


class SessionCreateRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)


class SessionCreateApiRequest(BaseModel):
    inputType: Literal["TEXT", "SKETCH", "TEXT_WITH_SKETCH"] = "TEXT"
    inputText: str | None = None
    inputImageUrl: str | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    project_id: str
    status: Literal["created"]
    created_at: str
    contract_version: Literal["v1"] = CONTRACT_VERSION


class SessionCreateApiResponse(BaseModel):
    sessionId: str
    versionNo: int
    status: str


class AnalyzeRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=2000)
    input_type: Literal["text", "sketch"] = "text"


class ArchitectureSaveRequest(BaseModel):
    schemaVersion: str = "v1"
    architectureJson: dict[str, Any]


class TerraformGenerateResponse(BaseModel):
    sessionId: str
    status: str
    validationStatus: str
    terraformCode: str
    validationOutput: str | None = None


class CostCalculateResponse(BaseModel):
    sessionId: str
    status: str
    currency: str
    region: str
    monthlyTotal: float
    costBreakdownJson: dict[str, Any]
    assumptionJson: dict[str, Any]


class ErrorPayload(BaseModel):
    code: Literal["PARSE_ERROR", "SCHEMA_ERROR", "TIMEOUT_ERROR", "INTERNAL_ERROR"]
    message: str


class AnalyzeResponse(BaseModel):
    session_id: str
    status: Literal["generated", "failed"]
    parsed_json: dict[str, Any] | None = None
    error: ErrorPayload | None = None
    contract_version: Literal["v1"] = CONTRACT_VERSION


def get_session_or_404(db: Session, session_id: str) -> AppSession:
    try:
        sid = UUID(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid session id") from e

    session = db.get(AppSession, sid)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return session


app = FastAPI(title="Sketch-to-Cloud API", version=CONTRACT_VERSION)


@app.post("/api/projects", response_model=ProjectCreateResponse)
def create_project(payload: ProjectCreateRequest, db: Session = Depends(get_db)) -> ProjectCreateResponse:
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectCreateResponse(projectId=str(project.id), name=project.name)


@app.get("/api/projects", response_model=list[ProjectListItem])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectListItem]:
    rows = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    return [ProjectListItem(projectId=str(p.id), name=p.name, description=p.description) for p in rows]


@app.post("/api/projects/{project_id}/sessions", response_model=SessionCreateApiResponse)
def create_project_session(
    project_id: str, payload: SessionCreateApiRequest, db: Session = Depends(get_db)
) -> SessionCreateApiResponse:
    try:
        pid = UUID(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid project id") from e

    project = db.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

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
        contract_version=CONTRACT_VERSION,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionCreateApiResponse(sessionId=str(session.id), versionNo=session.version_no, status=session.status)


@app.get("/api/projects/{project_id}/sessions")
def list_project_sessions(project_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    try:
        pid = UUID(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid project id") from e

    project = db.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    rows = db.scalars(
        select(AppSession).where(AppSession.project_id == pid).order_by(AppSession.version_no.desc())
    ).all()
    return [
        {
            "sessionId": str(s.id),
            "versionNo": s.version_no,
            "status": s.status,
            "createdAt": dt_to_iso(s.created_at),
        }
        for s in rows
    ]


@app.post("/api/sessions/{session_id}/architecture")
def save_architecture(
    session_id: str, payload: ArchitectureSaveRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    session = get_session_or_404(db, session_id)

    try:
        validate(instance=payload.architectureJson, schema=ARCH_SCHEMA)
    except ValidationError as e:
        session.status = "FAILED"
        session.error_code = "SCHEMA_ERROR"
        session.error_message = e.message
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=422, detail=f"schema validation failed: {e.message}") from e

    session.status = "ANALYZED"
    session.error_code = None
    session.error_message = None
    session.updated_at = datetime.now(timezone.utc)

    architecture = db.scalars(
        select(SessionArchitecture).where(SessionArchitecture.session_id == session.id).limit(1)
    ).first()
    if architecture:
        architecture.schema_version = payload.schemaVersion
        architecture.architecture_json = payload.architectureJson
    else:
        architecture = SessionArchitecture(
            session_id=session.id, schema_version=payload.schemaVersion, architecture_json=payload.architectureJson
        )
        db.add(architecture)

    db.commit()
    return {"sessionId": str(session.id), "status": session.status}


@app.get("/api/sessions/{session_id}")
def get_session_detail(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    session = get_session_or_404(db, session_id)
    architecture = db.scalars(
        select(SessionArchitecture).where(SessionArchitecture.session_id == session.id).limit(1)
    ).first()
    terraform_result = db.scalars(
        select(SessionTerraformResult).where(SessionTerraformResult.session_id == session.id).limit(1)
    ).first()
    cost_result = db.scalars(select(SessionCostResult).where(SessionCostResult.session_id == session.id).limit(1)).first()

    error = None
    if session.error_code or session.error_message:
        error = {"code": session.error_code, "message": session.error_message}

    return {
        "sessionId": str(session.id),
        "projectId": str(session.project_id),
        "versionNo": session.version_no,
        "inputType": session.input_type,
        "inputText": session.input_text,
        "status": session.status,
        "architecture": (
            {
                "schemaVersion": architecture.schema_version,
                "architectureJson": architecture.architecture_json,
            }
            if architecture
            else None
        ),
        "terraform": (
            {
                "validationStatus": terraform_result.validation_status,
                "terraformCode": terraform_result.terraform_code,
                "validationOutput": terraform_result.validation_output,
            }
            if terraform_result
            else None
        ),
        "cost": (
            {
                "currency": cost_result.currency,
                "region": cost_result.region,
                "monthlyTotal": float(cost_result.monthly_total),
                "costBreakdownJson": cost_result.cost_breakdown_json,
                "assumptionJson": cost_result.assumption_json,
            }
            if cost_result
            else None
        ),
        "error": error,
    }


@app.post("/api/sessions/{session_id}/terraform", response_model=TerraformGenerateResponse)
def generate_terraform(session_id: str, db: Session = Depends(get_db)) -> TerraformGenerateResponse:
    session = get_session_or_404(db, session_id)
    architecture = db.scalars(
        select(SessionArchitecture).where(SessionArchitecture.session_id == session.id).limit(1)
    ).first()
    if not architecture:
        raise HTTPException(status_code=409, detail="architecture not found for this session")

    session.status = "GENERATING_TERRAFORM"
    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    try:
        terraform_code = generate_terraform_from_architecture(architecture.architecture_json)
        validation_status, validation_output = validate_terraform_code(terraform_code)
        terraform_result = db.scalars(
            select(SessionTerraformResult).where(SessionTerraformResult.session_id == session.id).limit(1)
        ).first()
        if terraform_result:
            terraform_result.terraform_code = terraform_code
            terraform_result.validation_status = validation_status
            terraform_result.validation_output = validation_output
        else:
            terraform_result = SessionTerraformResult(
                session_id=session.id,
                terraform_code=terraform_code,
                validation_status=validation_status,
                validation_output=validation_output,
            )
            db.add(terraform_result)

        session.status = "GENERATED"
        session.error_code = None
        session.error_message = None
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        return TerraformGenerateResponse(
            sessionId=str(session.id),
            status=session.status,
            validationStatus=validation_status,
            terraformCode=terraform_code,
            validationOutput=validation_output,
        )
    except Exception as e:  # noqa: BLE001
        session.status = "FAILED"
        session.error_code = "INTERNAL_ERROR"
        session.error_message = str(e)
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail="terraform generation failed") from e


@app.post("/api/sessions/{session_id}/cost", response_model=CostCalculateResponse)
def calculate_cost(session_id: str, db: Session = Depends(get_db)) -> CostCalculateResponse:
    session = get_session_or_404(db, session_id)
    architecture = db.scalars(
        select(SessionArchitecture).where(SessionArchitecture.session_id == session.id).limit(1)
    ).first()
    if not architecture:
        raise HTTPException(status_code=409, detail="architecture not found for this session")

    try:
        cost = estimate_monthly_cost(architecture.architecture_json)
        cost_result = db.scalars(select(SessionCostResult).where(SessionCostResult.session_id == session.id).limit(1)).first()
        if cost_result:
            cost_result.currency = cost["currency"]
            cost_result.region = cost["region"]
            cost_result.assumption_json = cost["assumptions"]
            cost_result.monthly_total = cost["monthly_total"]
            cost_result.cost_breakdown_json = cost["breakdown"]
        else:
            cost_result = SessionCostResult(
                session_id=session.id,
                currency=cost["currency"],
                region=cost["region"],
                assumption_json=cost["assumptions"],
                monthly_total=cost["monthly_total"],
                cost_breakdown_json=cost["breakdown"],
            )
            db.add(cost_result)

        session.status = "COST_CALCULATED"
        session.error_code = None
        session.error_message = None
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        return CostCalculateResponse(
            sessionId=str(session.id),
            status=session.status,
            currency=cost["currency"],
            region=cost["region"],
            monthlyTotal=float(cost["monthly_total"]),
            costBreakdownJson=cost["breakdown"],
            assumptionJson=cost["assumptions"],
        )
    except Exception as e:  # noqa: BLE001
        session.status = "FAILED"
        session.error_code = "INTERNAL_ERROR"
        session.error_message = str(e)
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail="cost calculation failed") from e


# Backward-compatible endpoints used in early A-pipeline tests.
@app.post("/sessions", response_model=SessionCreateResponse)
def create_session(payload: SessionCreateRequest, db: Session = Depends(get_db)) -> SessionCreateResponse:
    try:
        pid = UUID(payload.project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="project_id must be UUID") from e

    project = db.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    latest = db.scalars(
        select(AppSession).where(AppSession.project_id == pid).order_by(AppSession.version_no.desc()).limit(1)
    ).first()
    next_version = 1 if not latest else latest.version_no + 1

    session = AppSession(
        project_id=pid,
        version_no=next_version,
        input_type="TEXT",
        input_text="",
        status="CREATED",
        contract_version=CONTRACT_VERSION,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionCreateResponse(
        session_id=str(session.id),
        project_id=str(session.project_id),
        status="created",
        created_at=dt_to_iso(session.created_at),
    )


@app.post("/sessions/{session_id}/analyze", response_model=AnalyzeResponse)
def analyze_session(session_id: str, payload: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    session = get_session_or_404(db, session_id)
    session.status = "ANALYZING"
    session.input_text = payload.input_text
    session.input_type = "SKETCH" if payload.input_type == "sketch" else "TEXT"
    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    try:
        parsed = parse_architecture_with_retry(payload.input_text, ARCH_SCHEMA)

        architecture = db.scalars(
            select(SessionArchitecture).where(SessionArchitecture.session_id == session.id).limit(1)
        ).first()
        if architecture:
            architecture.architecture_json = parsed
            architecture.schema_version = CONTRACT_VERSION
        else:
            architecture = SessionArchitecture(
                session_id=session.id,
                schema_version=CONTRACT_VERSION,
                architecture_json=parsed,
            )
            db.add(architecture)

        session.status = "GENERATED"
        session.error_code = None
        session.error_message = None
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        return AnalyzeResponse(session_id=session_id, status="generated", parsed_json=parsed)
    except AIParseError as e:
        session.status = "FAILED"
        session.error_code = e.code
        session.error_message = e.message
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        return AnalyzeResponse(session_id=session_id, status="failed", error=ErrorPayload(code=e.code, message=e.message))
    except Exception as e:  # noqa: BLE001
        session.status = "FAILED"
        session.error_code = "INTERNAL_ERROR"
        session.error_message = str(e)
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        return AnalyzeResponse(
            session_id=session_id, status="failed", error=ErrorPayload(code="INTERNAL_ERROR", message=str(e))
        )


@app.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    session = get_session_or_404(db, session_id)
    architecture = db.scalars(
        select(SessionArchitecture).where(SessionArchitecture.session_id == session.id).limit(1)
    ).first()
    error = (
        {"code": session.error_code, "message": session.error_message}
        if (session.error_code or session.error_message)
        else None
    )
    return {
        "session_id": str(session.id),
        "project_id": str(session.project_id),
        "status": session.status,
        "input_text": session.input_text or "",
        "parsed_json": architecture.architecture_json if architecture else None,
        "error": error,
        "created_at": dt_to_iso(session.created_at),
        "updated_at": dt_to_iso(session.updated_at),
        "contract_version": CONTRACT_VERSION,
    }
