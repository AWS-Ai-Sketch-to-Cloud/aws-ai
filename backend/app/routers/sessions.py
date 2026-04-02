from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from jsonschema import ValidationError, validate
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.ai_parser import AIParseError, parse_architecture_with_retry
import app.database as database_module
from app.core.constants import ARCH_SCHEMA, CONTRACT_VERSION, dt_to_iso
from app.core.deps import get_current_user
from app.cost_calculator import estimate_monthly_cost
from app.database import get_db
from app.models import (
    AppSession,
    Project,
    SessionArchitecture,
    SessionCostResult,
    SessionDeployment,
    SessionTerraformResult,
    User,
    UserDeployConfig,
)
from app.schemas.session import (
    AnalysisMeta,
    AnalyzeRequest,
    AnalyzeResponse,
    ArchitectureSaveRequest,
    CostCalculateResponse,
    DeployRequest,
    DestroyRequest,
    ErrorPayload,
    SessionCompareResponse,
    SessionDeploymentItem,
    SessionDeploymentListResponse,
    SessionDeploymentResponse,
    SessionDetailArchitecture,
    SessionDetailCost,
    SessionDetailError,
    SessionDetailResponse,
    SessionDetailTerraform,
    SessionResultResponse,
    SessionStatusPatchRequest,
    SessionStatusPatchResponse,
    TerraformGenerateResponse,
)
from app.services.deployment_service import resolve_credentials, run_deploy, run_destroy
from app.services.compare_service import (
    build_cost_diff,
    build_session_summary,
    build_terraform_diff,
    collect_json_diff,
)
from app.services.session_service import (
    ensure_session_access,
    get_compare_base_session,
    get_session_or_404,
    record_session_event,
    transition_session_status,
)
from app.terraform_generator import generate_terraform_from_architecture
from app.terraform_validator import validate_terraform_code

router = APIRouter()


def _to_deployment_item(deployment: SessionDeployment) -> SessionDeploymentItem:
    return SessionDeploymentItem(
        deploymentId=str(deployment.id),
        action=deployment.action,
        status=deployment.status,
        region=deployment.region,
        startedAt=dt_to_iso(deployment.started_at) if deployment.started_at else None,
        completedAt=dt_to_iso(deployment.completed_at) if deployment.completed_at else None,
        createdAt=dt_to_iso(deployment.created_at),
        log=deployment.log_text,
        appliedResources=deployment.applied_resources_json,
    )


def _build_destroy_confirmation_code(session_id: str) -> str:
    normalized = session_id.replace("-", "")
    return f"DESTROY-{normalized[-6:].upper()}"


def _resolve_user_assume_role(db: Session, user: User) -> tuple[str | None, str | None, str | None]:
    role_arn: str | None = None
    role_external_id: str | None = None
    role_session_name: str | None = None

    try:
        user_config = db.scalars(select(UserDeployConfig).where(UserDeployConfig.user_id == user.id).limit(1)).first()
    except ProgrammingError:
        db.rollback()
        user_config = None
    if user_config:
        role_arn = user_config.role_arn
        role_external_id = user_config.role_external_id
        role_session_name = user_config.role_session_name
        return role_arn, role_external_id, role_session_name or f"stc-{str(user.id).replace('-', '')[:12]}"

    raw_map = os.getenv("DEPLOY_USER_ROLE_MAP", "").strip()
    if raw_map:
        try:
            mapping = json.loads(raw_map)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"DEPLOY_USER_ROLE_MAP is not valid JSON: {e.msg}") from e
        if isinstance(mapping, dict):
            for lookup_key in (str(user.id), user.login_id, user.email):
                candidate = mapping.get(lookup_key)
                if candidate is None:
                    continue
                if isinstance(candidate, str):
                    role_arn = candidate.strip() or None
                elif isinstance(candidate, dict):
                    role_arn = str(candidate.get("roleArn", "")).strip() or None
                    role_external_id = str(candidate.get("roleExternalId", "")).strip() or None
                    role_session_name = str(candidate.get("roleSessionName", "")).strip() or None
                break

    if not role_arn:
        role_arn = os.getenv("DEPLOY_ASSUME_ROLE_ARN", "").strip() or None
        role_external_id = os.getenv("DEPLOY_ASSUME_ROLE_EXTERNAL_ID", "").strip() or None
        role_session_name = os.getenv("DEPLOY_ASSUME_ROLE_SESSION_NAME", "").strip() or None

    if role_session_name is None:
        role_session_name = f"stc-{str(user.id).replace('-', '')[:12]}"

    return role_arn, role_external_id, role_session_name


def _execute_deployment_job(
    *,
    deployment_id: str,
    session_id: str,
    action: str,
    terraform_code: str,
    auth_mode: str,
    access_key_id: str | None,
    secret_access_key: str | None,
    session_token: str | None,
    role_arn: str | None,
    role_external_id: str | None,
    role_session_name: str | None,
    region: str,
    simulate: bool,
) -> None:
    database_module._ensure_engine()
    if database_module.SessionLocal is None:
        raise RuntimeError("database session factory is not initialized")
    db = database_module.SessionLocal()
    try:
        deployment_row = db.get(SessionDeployment, UUID(deployment_id))
        session = get_session_or_404(db, session_id)
        if not deployment_row:
            return
        deployment_row.status = "RUNNING"
        deployment_row.started_at = datetime.now(timezone.utc)
        deployment_row.log_text = f"[{action.lower()}] running"
        db.commit()

        credentials = resolve_credentials(
            auth_mode=auth_mode,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
            role_arn=role_arn,
            role_external_id=role_external_id,
            role_session_name=role_session_name,
            region=region,
            simulate=simulate,
        )
        if action == "DEPLOY":
            result = run_deploy(terraform_code=terraform_code, credentials=credentials, region=region, simulate=simulate)
            event_ok = "DEPLOY_SUCCEEDED"
            event_fail = "DEPLOY_FAILED"
        else:
            result = run_destroy(terraform_code=terraform_code, credentials=credentials, region=region, simulate=simulate)
            event_ok = "DESTROY_SUCCEEDED"
            event_fail = "DESTROY_FAILED"

        deployment_row.status = result.status
        deployment_row.log_text = result.log
        deployment_row.applied_resources_json = result.resources
        deployment_row.completed_at = datetime.now(timezone.utc)
        deployment_row.updated_at = datetime.now(timezone.utc)
        record_session_event(
            db,
            session,
            event_ok if result.status == "SUCCEEDED" else event_fail,
            {"deploymentId": str(deployment_row.id), "region": region},
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        deployment_row = db.get(SessionDeployment, UUID(deployment_id))
        session = db.get(AppSession, UUID(session_id))
        if deployment_row:
            deployment_row.status = "FAILED"
            deployment_row.log_text = f"[{action.lower()}] failed\n{e}"
            deployment_row.completed_at = datetime.now(timezone.utc)
            deployment_row.updated_at = datetime.now(timezone.utc)
            if session:
                record_session_event(
                    db,
                    session,
                    "DEPLOY_FAILED" if action == "DEPLOY" else "DESTROY_FAILED",
                    {"deploymentId": str(deployment_row.id), "error": str(e), "region": region},
                )
            db.commit()
    finally:
        db.close()


def _analyze_session_impl(
    session_id: str,
    payload: AnalyzeRequest,
    db: Session,
    current_user: User,
) -> AnalyzeResponse:
    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)
    transition_session_status(db, session, "ANALYZING")
    session.input_text = payload.inputText
    session.input_type = "SKETCH" if payload.inputType == "sketch" else "TEXT"
    db.commit()

    try:
        parsed, analysis_meta = parse_architecture_with_retry(
            payload.inputText, ARCH_SCHEMA, payload.inputImageDataUrl
        )

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

        transition_session_status(db, session, "ANALYZED")
        record_session_event(db, session, "ARCHITECTURE_GENERATED", {"schemaVersion": CONTRACT_VERSION})
        db.commit()
        return AnalyzeResponse(
            sessionId=session_id,
            status="generated",
            parsedJson=parsed,
            analysisMeta=AnalysisMeta(**analysis_meta),
        )
    except AIParseError as e:
        transition_session_status(db, session, "FAILED", error_code=e.code, error_message=e.message)
        db.commit()
        return AnalyzeResponse(sessionId=session_id, status="failed", error=ErrorPayload(code=e.code, message=e.message))
    except Exception as e:  # noqa: BLE001
        transition_session_status(db, session, "FAILED", error_code="INTERNAL_ERROR", error_message=str(e))
        db.commit()
        return AnalyzeResponse(
            sessionId=session_id, status="failed", error=ErrorPayload(code="INTERNAL_ERROR", message=str(e))
        )


@router.post("/api/sessions/{session_id}/architecture", response_model=SessionResultResponse)
def save_architecture(
    session_id: str,
    payload: ArchitectureSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResultResponse:
    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)

    try:
        validate(instance=payload.architectureJson, schema=ARCH_SCHEMA)
    except ValidationError as e:
        transition_session_status(db, session, "FAILED", error_code="SCHEMA_ERROR", error_message=e.message)
        db.commit()
        raise HTTPException(status_code=422, detail=f"schema validation failed: {e.message}") from e

    transition_session_status(db, session, "ANALYZED")

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

    record_session_event(
        db,
        session,
        "ARCHITECTURE_SAVED",
        {"schemaVersion": payload.schemaVersion},
    )
    db.commit()
    return SessionResultResponse(sessionId=str(session.id), status=session.status)


@router.get("/api/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionDetailResponse:
    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)
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

    return SessionDetailResponse(
        sessionId=str(session.id),
        projectId=str(session.project_id),
        versionNo=session.version_no,
        inputType=session.input_type,
        inputText=session.input_text,
        inputImageUrl=session.input_image_url,
        status=session.status,
        architecture=(
            SessionDetailArchitecture(
                schemaVersion=architecture.schema_version,
                architectureJson=architecture.architecture_json,
            )
            if architecture
            else None
        ),
        terraform=(
            SessionDetailTerraform(
                validationStatus=terraform_result.validation_status,
                terraformCode=terraform_result.terraform_code,
                validationOutput=terraform_result.validation_output,
            )
            if terraform_result
            else None
        ),
        cost=(
            SessionDetailCost(
                currency=cost_result.currency,
                region=cost_result.region,
                monthlyTotal=float(cost_result.monthly_total),
                costBreakdownJson=cost_result.cost_breakdown_json,
                assumptionJson=cost_result.assumption_json,
            )
            if cost_result
            else None
        ),
        error=SessionDetailError(**error) if error else None,
        createdAt=dt_to_iso(session.created_at),
        updatedAt=dt_to_iso(session.updated_at),
    )


@router.get("/api/sessions/{session_id}/compare", response_model=SessionCompareResponse)
def compare_session_detail(
    session_id: str,
    baseSessionId: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionCompareResponse:
    target_session = get_session_or_404(db, session_id)
    ensure_session_access(target_session, current_user)
    base_session = get_compare_base_session(db, target_session, baseSessionId)
    ensure_session_access(base_session, current_user)

    base_architecture = db.scalars(
        select(SessionArchitecture).where(SessionArchitecture.session_id == base_session.id).limit(1)
    ).first()
    target_architecture = db.scalars(
        select(SessionArchitecture).where(SessionArchitecture.session_id == target_session.id).limit(1)
    ).first()
    base_terraform = db.scalars(
        select(SessionTerraformResult).where(SessionTerraformResult.session_id == base_session.id).limit(1)
    ).first()
    target_terraform = db.scalars(
        select(SessionTerraformResult).where(SessionTerraformResult.session_id == target_session.id).limit(1)
    ).first()
    base_cost = db.scalars(
        select(SessionCostResult).where(SessionCostResult.session_id == base_session.id).limit(1)
    ).first()
    target_cost = db.scalars(
        select(SessionCostResult).where(SessionCostResult.session_id == target_session.id).limit(1)
    ).first()

    json_diff = collect_json_diff(
        base_architecture.architecture_json if base_architecture else {},
        target_architecture.architecture_json if target_architecture else {},
    )
    terraform_diff = build_terraform_diff(
        base_terraform.terraform_code if base_terraform else None,
        target_terraform.terraform_code if target_terraform else None,
    )
    cost_diff = build_cost_diff(base_cost, target_cost)

    return SessionCompareResponse(
        baseSession=build_session_summary(base_session),
        targetSession=build_session_summary(target_session),
        jsonDiff=json_diff,
        terraformDiff=terraform_diff,
        costDiff=cost_diff,
    )


@router.patch("/api/sessions/{session_id}/status", response_model=SessionStatusPatchResponse)
def patch_session_status(
    session_id: str,
    payload: SessionStatusPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionStatusPatchResponse:
    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)
    transition_session_status(
        db,
        session,
        payload.status,
        error_code=payload.errorCode,
        error_message=payload.errorMessage,
    )
    db.commit()
    return SessionStatusPatchResponse(sessionId=str(session.id), status=session.status)


@router.post("/api/sessions/{session_id}/terraform", response_model=TerraformGenerateResponse)
def generate_terraform(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TerraformGenerateResponse:
    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)
    architecture = db.scalars(
        select(SessionArchitecture).where(SessionArchitecture.session_id == session.id).limit(1)
    ).first()
    if not architecture:
        raise HTTPException(status_code=409, detail="architecture not found for this session")

    transition_session_status(db, session, "GENERATING_TERRAFORM")
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

        transition_session_status(db, session, "GENERATED")
        record_session_event(
            db,
            session,
            "TERRAFORM_GENERATED",
            {"validationStatus": validation_status},
        )
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
        transition_session_status(db, session, "FAILED", error_code="INTERNAL_ERROR", error_message=str(e))
        db.commit()
        raise HTTPException(status_code=500, detail="terraform generation failed") from e


@router.post("/api/sessions/{session_id}/cost", response_model=CostCalculateResponse)
def calculate_cost(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostCalculateResponse:
    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)
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

        transition_session_status(db, session, "COST_CALCULATED")
        record_session_event(
            db,
            session,
            "COST_CALCULATED",
            {"monthlyTotal": cost["monthly_total"], "region": cost["region"]},
        )
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
        transition_session_status(db, session, "FAILED", error_code="INTERNAL_ERROR", error_message=str(e))
        db.commit()
        raise HTTPException(status_code=500, detail="cost calculation failed") from e


@router.post("/api/sessions/{session_id}/analyze", response_model=AnalyzeResponse)
def analyze_session_api(
    session_id: str,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyzeResponse:
    return _analyze_session_impl(session_id, payload, db, current_user)


@router.post("/api/sessions/{session_id}/deploy", response_model=SessionDeploymentResponse)
def deploy_session(
    session_id: str,
    payload: DeployRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionDeploymentResponse:
    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)
    terraform_result = db.scalars(
        select(SessionTerraformResult).where(SessionTerraformResult.session_id == session.id).limit(1)
    ).first()
    if not terraform_result or not terraform_result.terraform_code:
        raise HTTPException(status_code=409, detail="terraform result not found for this session")

    region = payload.awsRegion or "ap-northeast-2"
    role_arn, role_external_id, role_session_name = _resolve_user_assume_role(db, current_user)
    if not payload.simulate and not role_arn:
        raise HTTPException(
            status_code=400,
            detail="deploy role is not configured for this user. configure DEPLOY_USER_ROLE_MAP or DEPLOY_ASSUME_ROLE_ARN",
        )
    deployment = SessionDeployment(
        session_id=session.id,
        action="DEPLOY",
        status="PENDING",
        region=region,
        log_text="[deployment] queued",
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    background_tasks.add_task(
        _execute_deployment_job,
        deployment_id=str(deployment.id),
        session_id=str(session.id),
        action="DEPLOY",
        terraform_code=terraform_result.terraform_code,
        auth_mode="ASSUME_ROLE",
        access_key_id=None,
        secret_access_key=None,
        session_token=None,
        role_arn=role_arn,
        role_external_id=role_external_id,
        role_session_name=role_session_name,
        region=region,
        simulate=payload.simulate,
    )
    record_session_event(db, session, "DEPLOY_QUEUED", {"deploymentId": str(deployment.id), "region": region})
    db.commit()
    return SessionDeploymentResponse(item=_to_deployment_item(deployment))


@router.post("/api/sessions/{session_id}/destroy", response_model=SessionDeploymentResponse)
def destroy_session(
    session_id: str,
    payload: DestroyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionDeploymentResponse:
    if not payload.confirmDestroy:
        raise HTTPException(status_code=400, detail="confirmDestroy must be true")
    expected_code = _build_destroy_confirmation_code(session_id)
    if payload.confirmationCode != expected_code:
        raise HTTPException(status_code=400, detail=f"invalid confirmationCode. expected: {expected_code}")

    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)
    terraform_result = db.scalars(
        select(SessionTerraformResult).where(SessionTerraformResult.session_id == session.id).limit(1)
    ).first()
    if not terraform_result or not terraform_result.terraform_code:
        raise HTTPException(status_code=409, detail="terraform result not found for this session")

    region = payload.awsRegion or "ap-northeast-2"
    role_arn, role_external_id, role_session_name = _resolve_user_assume_role(db, current_user)
    if not payload.simulate and not role_arn:
        raise HTTPException(
            status_code=400,
            detail="deploy role is not configured for this user. configure DEPLOY_USER_ROLE_MAP or DEPLOY_ASSUME_ROLE_ARN",
        )
    deployment = SessionDeployment(
        session_id=session.id,
        action="DESTROY",
        status="PENDING",
        region=region,
        log_text="[destroy] queued",
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    background_tasks.add_task(
        _execute_deployment_job,
        deployment_id=str(deployment.id),
        session_id=str(session.id),
        action="DESTROY",
        terraform_code=terraform_result.terraform_code,
        auth_mode="ASSUME_ROLE",
        access_key_id=None,
        secret_access_key=None,
        session_token=None,
        role_arn=role_arn,
        role_external_id=role_external_id,
        role_session_name=role_session_name,
        region=region,
        simulate=payload.simulate,
    )
    record_session_event(db, session, "DESTROY_QUEUED", {"deploymentId": str(deployment.id), "region": region})
    db.commit()
    return SessionDeploymentResponse(item=_to_deployment_item(deployment))


@router.get("/api/sessions/{session_id}/deployments", response_model=SessionDeploymentListResponse)
def list_session_deployments(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionDeploymentListResponse:
    session = get_session_or_404(db, session_id)
    ensure_session_access(session, current_user)
    rows = db.scalars(
        select(SessionDeployment).where(SessionDeployment.session_id == session.id).order_by(SessionDeployment.created_at.desc())
    ).all()
    return SessionDeploymentListResponse(items=[_to_deployment_item(row) for row in rows])


