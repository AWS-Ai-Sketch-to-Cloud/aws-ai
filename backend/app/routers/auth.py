from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import dt_to_iso
from app.core.deps import get_current_user
from app.core.security import hash_text, to_access_token
from app.database import get_db
from app.models import AuthIdentity, AuthSession, User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LoginUser,
    LogoutRequest,
    LogoutResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter()


@router.post("/api/auth/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    existing_email = db.scalars(select(User).where(User.email == payload.email).limit(1)).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")

    existing_login = db.scalars(select(User).where(User.login_id == payload.loginId).limit(1)).first()
    if existing_login:
        raise HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다.")

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


@router.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalars(select(User).where(User.login_id == payload.loginId).limit(1)).first()
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.")

    if not user.password_hash or user.password_hash != hash_text(payload.password):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.")

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


@router.post("/api/auth/logout", response_model=LogoutResponse)
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


@router.get("/api/users/me", response_model=MeResponse)
def get_me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        userId=str(user.id),
        loginId=user.login_id,
        email=user.email,
        displayName=user.display_name,
        isActive=user.is_active,
        role=user.role,
        lastLoginAt=dt_to_iso(user.last_login_at) if user.last_login_at else None,
    )
