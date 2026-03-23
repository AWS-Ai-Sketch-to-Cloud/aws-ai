from __future__ import annotations

## uvicorn app.main:app --reload

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jsonschema import ValidationError, validate
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_parser import AIParseError, parse_architecture_with_retry
from app.cost_calculator import estimate_monthly_cost
from app.database import get_db
from app.models import (
    AppSession,
    AuthIdentity,
    AuthSession,
    Project,
    SessionArchitecture,
    SessionCostResult,
    SessionTerraformResult,
    User,
)
from app.terraform_generator import generate_terraform_from_architecture
from app.terraform_validator import validate_terraform_code

CONTRACT_VERSION = "v2"
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
    contract_version: Literal["v2"] = CONTRACT_VERSION


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
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class CostCalculateResponse(BaseModel):
    sessionId: str
    status: str
    currency: str
    region: str
    monthlyTotal: float
    costBreakdownJson: dict[str, Any]
    assumptionJson: dict[str, Any]
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class RegisterRequest(BaseModel):
    loginId: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    displayName: str = Field(min_length=1, max_length=100)


class RegisterResponse(BaseModel):
    userId: str
    loginId: str
    email: str
    displayName: str
    isActive: bool
    role: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class LoginRequest(BaseModel):
    loginId: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginUser(BaseModel):
    userId: str
    loginId: str
    email: str
    displayName: str
    role: str


class LoginResponse(BaseModel):
    user: LoginUser
    accessToken: str
    refreshToken: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class LogoutRequest(BaseModel):
    refreshToken: str = Field(min_length=10, max_length=500)


class LogoutResponse(BaseModel):
    success: bool
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class MeResponse(BaseModel):
    userId: str
    loginId: str
    email: str
    displayName: str
    isActive: bool
    role: str
    lastLoginAt: str | None = None
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class UploadImageRequest(BaseModel):
    contentType: str = Field(min_length=3, max_length=100)
    fileName: str = Field(min_length=1, max_length=255)


class UploadImageResponse(BaseModel):
    fileId: str
    url: str
    contentType: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class SessionStatusPatchRequest(BaseModel):
    status: Literal[
        "CREATED",
        "ANALYZING",
        "ANALYZED",
        "GENERATING_TERRAFORM",
        "GENERATED",
        "COST_CALCULATED",
        "FAILED",
    ]
    errorCode: str | None = Field(default=None, max_length=50)
    errorMessage: str | None = Field(default=None, max_length=2000)


class ErrorPayload(BaseModel):
    code: Literal["PARSE_ERROR", "SCHEMA_ERROR", "TIMEOUT_ERROR", "INTERNAL_ERROR"]
    message: str


class AnalyzeResponse(BaseModel):
    session_id: str
    status: Literal["generated", "failed"]
    parsed_json: dict[str, Any] | None = None
    error: ErrorPayload | None = None
    contract_version: Literal["v2"] = CONTRACT_VERSION


def hash_text(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def to_access_token(user_id: UUID) -> str:
    return f"uid:{user_id}"


def user_id_from_auth_header(authorization: str | None) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith("uid:"):
        raise HTTPException(status_code=401, detail="invalid access token")
    raw_user_id = token.removeprefix("uid:")
    try:
        return UUID(raw_user_id)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="invalid access token") from e


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/auth/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    existing_email = db.scalars(select(User).where(User.email == payload.email).limit(1)).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="email already exists")

    existing_login = db.scalars(select(User).where(User.login_id == payload.loginId).limit(1)).first()
    if existing_login:
        raise HTTPException(status_code=409, detail="loginId already exists")

    user = User(
        login_id=payload.loginId,
        email=payload.email,
        password_hash=hash_text(payload.password),
        display_name=payload.displayName,
        is_active=True,
        role="USER",
    )
    db.add(user)
    db.flush()

    identity = AuthIdentity(user_id=user.id, provider="LOCAL", provider_user_id=payload.loginId)
    db.add(identity)
    db.commit()

    return RegisterResponse(
        userId=str(user.id),
        loginId=payload.loginId,
        email=user.email,
        displayName=user.display_name,
        isActive=user.is_active,
        role=user.role,
    )


@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalars(select(User).where(User.login_id == payload.loginId).limit(1)).first()
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")

    if not user or not user.password_hash or user.password_hash != hash_text(payload.password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    refresh_token = secrets.token_urlsafe(48)
    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=hash_text(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(auth_session)
    user.last_login_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    return LoginResponse(
        user=LoginUser(
            userId=str(user.id),
            loginId=user.login_id,
            email=user.email,
            displayName=user.display_name,
            role=user.role,
        ),
        accessToken=to_access_token(user.id),
        refreshToken=refresh_token,
    )


@app.post("/api/auth/logout", response_model=LogoutResponse)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> LogoutResponse:
    refresh_hash = hash_text(payload.refreshToken)
    auth_session = db.scalars(
        select(AuthSession)
        .where(AuthSession.refresh_token_hash == refresh_hash, AuthSession.revoked_at.is_(None))
        .limit(1)
    ).first()
    if auth_session:
        auth_session.revoked_at = datetime.now(timezone.utc)
        auth_session.updated_at = datetime.now(timezone.utc)
        db.commit()
    return LogoutResponse(success=True)


@app.get("/api/users/me", response_model=MeResponse)
def get_me(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> MeResponse:
    user_id = user_id_from_auth_header(authorization)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    return MeResponse(
        userId=str(user.id),
        loginId=user.login_id,
        email=user.email,
        displayName=user.display_name,
        isActive=user.is_active,
        role=user.role,
        lastLoginAt=dt_to_iso(user.last_login_at) if user.last_login_at else None,
    )


@app.post("/api/uploads/images", response_model=UploadImageResponse)
def upload_image_stub(payload: UploadImageRequest) -> UploadImageResponse:
    file_id = uuid4()
    safe_file_name = payload.fileName.strip().replace(" ", "-")
    return UploadImageResponse(
        fileId=str(file_id),
        url=f"https://storage.example.com/uploads/{file_id}/{safe_file_name}",
        contentType=payload.contentType,
    )


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


@app.patch("/api/sessions/{session_id}/status")
def patch_session_status(
    session_id: str, payload: SessionStatusPatchRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    session = get_session_or_404(db, session_id)
    session.status = payload.status
    session.error_code = payload.errorCode
    session.error_message = payload.errorMessage
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"sessionId": str(session.id), "status": session.status}


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
            contractVersion=CONTRACT_VERSION,
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
            contractVersion=CONTRACT_VERSION,
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

