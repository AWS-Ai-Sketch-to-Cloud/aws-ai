from __future__ import annotations

import base64
import json
import logging
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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
    SocialSignupCompleteRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)

SUPPORTED_SOCIAL_PROVIDERS = {"google", "naver", "kakao", "github"}
SOCIAL_STATE_TTL = timedelta(minutes=10)
SOCIAL_STATE_STORE: dict[str, tuple[str, datetime]] = {}


class SocialSignupRequired(Exception):
    def __init__(self, *, provider: str, provider_user_id: str, email: str, display_name: str) -> None:
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.email = email
        self.display_name = display_name
        super().__init__("social signup required")


def _normalize_social_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_SOCIAL_PROVIDERS:
        raise HTTPException(status_code=404, detail="지원하지 않는 소셜 로그인 제공자입니다.")
    return normalized


def _prune_social_states() -> None:
    now = datetime.now(timezone.utc)
    expired_states = [state for state, (_, expires_at) in SOCIAL_STATE_STORE.items() if expires_at <= now]
    for state in expired_states:
        SOCIAL_STATE_STORE.pop(state, None)


def _social_frontend_redirect_url() -> str:
    return os.getenv("SOCIAL_LOGIN_REDIRECT_URL", "http://127.0.0.1:5173/auth/social/callback")


def _social_config(provider: str, request: Request) -> dict[str, str]:
    env_prefix = provider.upper()
    client_id = os.getenv(f"{env_prefix}_OAUTH_CLIENT_ID")
    client_secret = os.getenv(f"{env_prefix}_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail=f"{provider.upper()} OAuth 설정이 아직 완료되지 않았습니다.")

    return {
        "provider": provider,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": str(request.url_for("social_callback", provider=provider)),
    }


def _build_social_authorization_url(config: dict[str, str], state: str) -> str:
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "state": state,
    }

    if config["provider"] == "google":
        params["scope"] = "openid email profile"
        params["prompt"] = "select_account"
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    if config["provider"] == "naver":
        return "https://nid.naver.com/oauth2.0/authorize?" + urllib.parse.urlencode(params)

    if config["provider"] == "github":
        params["scope"] = "read:user user:email"
        return "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)

    return "https://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode(params)


def _request_json(
    url: str,
    *,
    method: str = "GET",
    form_data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> dict | list:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)

    encoded_body = None
    if form_data is not None:
        encoded_body = urllib.parse.urlencode(form_data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = urllib.request.Request(url=url, data=encoded_body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=502, detail=f"소셜 로그인 연동 중 오류가 발생했습니다. {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail="소셜 로그인 제공자와 통신할 수 없습니다.") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="소셜 로그인 응답을 해석할 수 없습니다.") from exc


def _exchange_social_code(config: dict[str, str], code: str, state: str) -> str:
    if config["provider"] == "google":
        response = _request_json(
            "https://oauth2.googleapis.com/token",
            method="POST",
            form_data={
                "code": code,
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "redirect_uri": config["redirect_uri"],
                "grant_type": "authorization_code",
            },
        )
        access_token = response.get("access_token") if isinstance(response, dict) else None
        if not access_token:
            raise HTTPException(status_code=502, detail="구글 액세스 토큰을 받지 못했습니다.")
        return str(access_token)

    if config["provider"] == "naver":
        response = _request_json(
            "https://nid.naver.com/oauth2.0/token",
            method="POST",
            form_data={
                "grant_type": "authorization_code",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "state": state,
            },
        )
        access_token = response.get("access_token") if isinstance(response, dict) else None
        if not access_token:
            raise HTTPException(status_code=502, detail="네이버 액세스 토큰을 받지 못했습니다.")
        return str(access_token)

    if config["provider"] == "github":
        response = _request_json(
            "https://github.com/login/oauth/access_token",
            method="POST",
            form_data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "redirect_uri": config["redirect_uri"],
            },
        )
        access_token = response.get("access_token") if isinstance(response, dict) else None
        if not access_token:
            raise HTTPException(status_code=502, detail="GitHub 액세스 토큰을 받지 못했습니다.")
        return str(access_token)

    response = _request_json(
        "https://kauth.kakao.com/oauth/token",
        method="POST",
        form_data={
            "grant_type": "authorization_code",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "code": code,
        },
    )
    access_token = response.get("access_token") if isinstance(response, dict) else None
    if not access_token:
        raise HTTPException(status_code=502, detail="카카오 액세스 토큰을 받지 못했습니다.")
    return str(access_token)


def _load_social_profile(config: dict[str, str], access_token: str) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {access_token}"}

    if config["provider"] == "google":
        response = _request_json("https://openidconnect.googleapis.com/v1/userinfo", headers=headers)
        if not isinstance(response, dict):
            raise HTTPException(status_code=502, detail="구글 사용자 정보를 확인할 수 없습니다.")
        provider_user_id = str(response.get("sub", "")).strip()
        email = str(response.get("email", "")).strip()
        display_name = str(response.get("name", "")).strip() or email.split("@")[0]
        if not provider_user_id:
            raise HTTPException(status_code=502, detail="구글 사용자 정보를 확인할 수 없습니다.")
        return {
            "provider_user_id": provider_user_id,
            "email": email or f"google_{provider_user_id}@social.local",
            "display_name": display_name or "Google User",
        }

    if config["provider"] == "naver":
        response = _request_json("https://openapi.naver.com/v1/nid/me", headers=headers)
        profile = response.get("response", {}) if isinstance(response, dict) else {}
        provider_user_id = str(profile.get("id", "")).strip()
        email = str(profile.get("email", "")).strip()
        display_name = (
            str(profile.get("name", "")).strip()
            or str(profile.get("nickname", "")).strip()
            or email.split("@")[0]
        )
        if not provider_user_id:
            raise HTTPException(status_code=502, detail="네이버 사용자 정보를 확인할 수 없습니다.")
        return {
            "provider_user_id": provider_user_id,
            "email": email or f"naver_{provider_user_id}@social.local",
            "display_name": display_name or "Naver User",
        }

    if config["provider"] == "github":
        github_headers = headers | {"User-Agent": "Sketch-to-Cloud"}
        response = _request_json("https://api.github.com/user", headers=github_headers)
        if not isinstance(response, dict):
            raise HTTPException(status_code=502, detail="GitHub 사용자 정보를 확인할 수 없습니다.")
        provider_user_id = str(response.get("id", "")).strip()
        email = str(response.get("email", "")).strip()
        display_name = (
            str(response.get("name", "")).strip()
            or str(response.get("login", "")).strip()
            or email.split("@")[0]
        )
        if not email:
            emails_response = _request_json("https://api.github.com/user/emails", headers=github_headers)
            if isinstance(emails_response, list):
                primary_email = next(
                    (
                        item.get("email")
                        for item in emails_response
                        if isinstance(item, dict) and item.get("primary") and item.get("verified")
                    ),
                    None,
                )
                fallback_email = next(
                    (
                        item.get("email")
                        for item in emails_response
                        if isinstance(item, dict) and item.get("verified")
                    ),
                    None,
                )
                email = str(primary_email or fallback_email or "").strip()
        if not provider_user_id:
            raise HTTPException(status_code=502, detail="GitHub 사용자 정보를 확인할 수 없습니다.")
        return {
            "provider_user_id": provider_user_id,
            "email": email or f"github_{provider_user_id}@social.local",
            "display_name": display_name or "GitHub User",
        }

    response = _request_json("https://kapi.kakao.com/v2/user/me", headers=headers)
    kakao_account = response.get("kakao_account", {}) if isinstance(response, dict) else {}
    profile = kakao_account.get("profile", {}) if isinstance(kakao_account, dict) else {}
    provider_user_id = str(response.get("id", "")).strip()
    email = str(kakao_account.get("email", "")).strip()
    display_name = (
        str(profile.get("nickname", "")).strip()
        or str(profile.get("name", "")).strip()
        or email.split("@")[0]
    )
    if not provider_user_id:
        raise HTTPException(status_code=502, detail="카카오 사용자 정보를 확인할 수 없습니다.")
    return {
        "provider_user_id": provider_user_id,
        "email": email or f"kakao_{provider_user_id}@social.local",
        "display_name": display_name or "Kakao User",
    }


def _normalize_login_id_seed(seed: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]", "", seed.lower())
    if len(cleaned) < 3:
        cleaned = f"{cleaned}user"
    return cleaned[:20]


def _issue_login_response(db: Session, user: User) -> LoginResponse:
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


def _generate_social_login_id(db: Session, provider: str, email: str, provider_user_id: str) -> str:
    email_seed = email.split("@")[0] if email else provider_user_id
    base_seed = _normalize_login_id_seed(f"{provider}{email_seed}")
    candidate = base_seed
    sequence = 0

    while db.scalars(select(User).where(User.login_id == candidate).limit(1)).first():
        raw_suffix = provider_user_id[-6:] if sequence == 0 else f"{provider_user_id[-4:]}{sequence}"
        suffix = _normalize_login_id_seed(raw_suffix)
        candidate = f"{base_seed[: max(3, 20 - len(suffix))]}{suffix}"
        sequence += 1

    return candidate


def _complete_social_signup(
    db: Session,
    *,
    provider: str,
    provider_user_id: str,
    email: str,
    display_name: str,
) -> LoginResponse:
    provider_name = provider.upper()

    existing_identity = db.scalars(
        select(AuthIdentity)
        .where(AuthIdentity.provider == provider_name, AuthIdentity.provider_user_id == provider_user_id)
        .limit(1)
    ).first()
    if existing_identity:
        return _issue_login_response(db, existing_identity.user)

    existing_email = db.scalars(select(User).where(User.email == email).limit(1)).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다. 기존 계정으로 로그인해 주세요.")

    user = User(
        login_id=_generate_social_login_id(db, provider, email, provider_user_id),
        email=email,
        password_hash=None,
        display_name=display_name,
        is_active=True,
        role="USER",
    )
    db.add(user)
    db.flush()

    db.add(AuthIdentity(user_id=user.id, provider=provider_name, provider_user_id=provider_user_id))
    db.flush()

    return _issue_login_response(db, user)


def _login_or_register_social_user(
    db: Session,
    *,
    provider: str,
    provider_user_id: str,
    email: str,
    display_name: str,
) -> LoginResponse:
    provider_name = provider.upper()

    identity = db.scalars(
        select(AuthIdentity)
        .where(AuthIdentity.provider == provider_name, AuthIdentity.provider_user_id == provider_user_id)
        .limit(1)
    ).first()
    if identity:
        return _issue_login_response(db, identity.user)

    user = db.scalars(select(User).where(User.email == email).limit(1)).first()
    if user is None:
        raise SocialSignupRequired(
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            display_name=display_name or email.split("@")[0],
        )

    user.display_name = display_name or user.display_name
    user.updated_at = datetime.now(timezone.utc)

    existing_provider_identity = db.scalars(
        select(AuthIdentity)
        .where(AuthIdentity.user_id == user.id, AuthIdentity.provider == provider_name)
        .limit(1)
    ).first()
    if existing_provider_identity:
        if existing_provider_identity.provider_user_id != provider_user_id:
            raise HTTPException(
                status_code=409,
                detail="이미 다른 소셜 계정이 연결되어 있습니다. 기존 계정으로 다시 시도해 주세요.",
            )
        return _issue_login_response(db, user)

    db.add(AuthIdentity(user_id=user.id, provider=provider_name, provider_user_id=provider_user_id))
    db.flush()

    return _issue_login_response(db, user)


def _encode_social_callback_payload(login_response: LoginResponse, provider: str) -> str:
    payload = {
        "provider": provider,
        "user": login_response.user.model_dump(),
        "accessToken": login_response.accessToken,
        "refreshToken": login_response.refreshToken,
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def _encode_social_signup_payload(
    *,
    provider: str,
    provider_user_id: str,
    email: str,
    display_name: str,
) -> str:
    payload = {
        "provider": provider,
        "providerUserId": provider_user_id,
        "email": email,
        "displayName": display_name,
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def _redirect_social_result(
    *,
    payload: str | None = None,
    error: str | None = None,
    signup_payload: str | None = None,
) -> RedirectResponse:
    fragment_params: dict[str, str] = {}
    if payload:
        fragment_params["payload"] = payload
    if error:
        fragment_params["error"] = error
    if signup_payload:
        fragment_params["signup"] = signup_payload
    fragment = urllib.parse.urlencode(fragment_params)
    return RedirectResponse(f"{_social_frontend_redirect_url()}#{fragment}", status_code=302)


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

    db.add(AuthIdentity(user_id=user.id, provider="LOCAL", provider_user_id=payload.loginId))
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

    return _issue_login_response(db, user)


@router.post("/api/auth/social/complete-signup", response_model=LoginResponse)
def complete_social_signup(
    payload: SocialSignupCompleteRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    try:
        return _complete_social_signup(
            db,
            provider=_normalize_social_provider(payload.provider),
            provider_user_id=payload.providerUserId,
            email=payload.email,
            display_name=payload.displayName,
        )
    except IntegrityError:
        db.rollback()
        logger.exception("Social signup integrity error for provider=%s", payload.provider)
        raise HTTPException(status_code=409, detail="소셜 계정 가입 처리 중 중복 데이터가 발생했습니다.")
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Social signup database error for provider=%s", payload.provider)
        raise HTTPException(status_code=500, detail="소셜 계정 가입 처리 중 데이터 저장에 실패했습니다.")


@router.get("/api/auth/social/{provider}/start")
def social_start(provider: str, request: Request) -> RedirectResponse:
    normalized_provider = _normalize_social_provider(provider)
    config = _social_config(normalized_provider, request)
    _prune_social_states()
    state = secrets.token_urlsafe(24)
    SOCIAL_STATE_STORE[state] = (normalized_provider, datetime.now(timezone.utc) + SOCIAL_STATE_TTL)
    return RedirectResponse(_build_social_authorization_url(config, state), status_code=302)


@router.get("/api/auth/social/{provider}/callback", name="social_callback")
def social_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    normalized_provider = _normalize_social_provider(provider)

    if error:
        return _redirect_social_result(error=f"{normalized_provider} 로그인에 실패했습니다: {error}")

    if not code or not state:
        return _redirect_social_result(error="소셜 로그인 응답에 필요한 값이 누락되었습니다.")

    _prune_social_states()
    stored_provider, expires_at = SOCIAL_STATE_STORE.pop(state, ("", datetime.now(timezone.utc)))
    if stored_provider != normalized_provider or expires_at <= datetime.now(timezone.utc):
        return _redirect_social_result(error="소셜 로그인 요청이 만료되었거나 올바르지 않습니다.")

    try:
        config = _social_config(normalized_provider, request)
        provider_access_token = _exchange_social_code(config, code, state)
        social_profile = _load_social_profile(config, provider_access_token)
        login_response = _login_or_register_social_user(
            db,
            provider=normalized_provider,
            provider_user_id=social_profile["provider_user_id"],
            email=social_profile["email"],
            display_name=social_profile["display_name"],
        )
    except HTTPException as exc:
        return _redirect_social_result(error=str(exc.detail))
    except SocialSignupRequired as exc:
        return _redirect_social_result(
            signup_payload=_encode_social_signup_payload(
                provider=exc.provider,
                provider_user_id=exc.provider_user_id,
                email=exc.email,
                display_name=exc.display_name,
            )
        )
    except IntegrityError:
        db.rollback()
        logger.exception("Social login integrity error for provider=%s", normalized_provider)
        return _redirect_social_result(error="소셜 로그인 계정 연결 중 중복 데이터가 발생했습니다. 다시 시도해 주세요.")
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Social login database error for provider=%s", normalized_provider)
        return _redirect_social_result(error="소셜 로그인 중 데이터 저장에 실패했습니다. 잠시 후 다시 시도해 주세요.")
    except Exception:
        db.rollback()
        logger.exception("Unexpected social login error for provider=%s", normalized_provider)
        return _redirect_social_result(error="소셜 로그인 처리 중 알 수 없는 오류가 발생했습니다.")

    return _redirect_social_result(payload=_encode_social_callback_payload(login_response, normalized_provider))


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
