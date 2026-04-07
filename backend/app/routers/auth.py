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

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.constants import dt_to_iso
from app.core.deps import get_current_user
from app.core.security import hash_text, to_access_token
from app.database import get_db
from app.models import AuthIdentity, AuthSession, User, UserDeployConfig
from app.schemas.auth import (
    AwsDeployConfigRequest,
    AwsDeployConfigResponse,
    AwsDeployGuideResponse,
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
from app.services.github_oauth_store import put_github_access_token

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


def _as_clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_social_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_SOCIAL_PROVIDERS:
        raise HTTPException(status_code=404, detail="吏?먰븯吏 ?딅뒗 ?뚯뀥 濡쒓렇???쒓났?먯엯?덈떎.")
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
    client_id = os.getenv(f"{env_prefix}_OAUTH_CLIENT_ID") or os.getenv(f"{env_prefix}_CLIENT_ID")
    client_secret = os.getenv(f"{env_prefix}_OAUTH_CLIENT_SECRET") or os.getenv(f"{env_prefix}_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail=(
                f"{provider.upper()} OAuth 설정이 아직 완료되지 않았습니다. "
                f"{env_prefix}_OAUTH_CLIENT_ID / {env_prefix}_OAUTH_CLIENT_SECRET "
                f"(또는 {env_prefix}_CLIENT_ID / {env_prefix}_CLIENT_SECRET) 값을 설정해 주세요."
            ),
        )

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
        params["scope"] = "read:user user:email repo read:org"
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
        raise HTTPException(status_code=502, detail=f"?뚯뀥 濡쒓렇???곕룞 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎. {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail="?뚯뀥 濡쒓렇???쒓났?먯? ?듭떊?????놁뒿?덈떎.") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="?뚯뀥 濡쒓렇???묐떟???댁꽍?????놁뒿?덈떎.") from exc


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
            raise HTTPException(status_code=502, detail="援ш? ?≪꽭???좏겙??諛쏆? 紐삵뻽?듬땲??")
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
            raise HTTPException(status_code=502, detail="?ㅼ씠踰??≪꽭???좏겙??諛쏆? 紐삵뻽?듬땲??")
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
            raise HTTPException(status_code=502, detail="GitHub ?≪꽭???좏겙??諛쏆? 紐삵뻽?듬땲??")
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
        raise HTTPException(status_code=502, detail="移댁뭅???≪꽭???좏겙??諛쏆? 紐삵뻽?듬땲??")
    return str(access_token)


def _load_social_profile(config: dict[str, str], access_token: str) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {access_token}"}

    if config["provider"] == "google":
        response = _request_json("https://openidconnect.googleapis.com/v1/userinfo", headers=headers)
        if not isinstance(response, dict):
            raise HTTPException(status_code=502, detail="援ш? ?ъ슜???뺣낫瑜??뺤씤?????놁뒿?덈떎.")
        provider_user_id = _as_clean_text(response.get("sub", ""))
        email = _as_clean_text(response.get("email", ""))
        display_name = _as_clean_text(response.get("name", "")) or email.split("@")[0]
        if not provider_user_id:
            raise HTTPException(status_code=502, detail="援ш? ?ъ슜???뺣낫瑜??뺤씤?????놁뒿?덈떎.")
        return {
            "provider_user_id": provider_user_id,
            "email": email or f"google_{provider_user_id}@social.local",
            "display_name": display_name or "Google User",
        }

    if config["provider"] == "naver":
        response = _request_json("https://openapi.naver.com/v1/nid/me", headers=headers)
        profile = response.get("response", {}) if isinstance(response, dict) else {}
        provider_user_id = _as_clean_text(profile.get("id", ""))
        email = _as_clean_text(profile.get("email", ""))
        display_name = (
            _as_clean_text(profile.get("name", ""))
            or _as_clean_text(profile.get("nickname", ""))
            or email.split("@")[0]
        )
        if not provider_user_id:
            raise HTTPException(status_code=502, detail="?ㅼ씠踰??ъ슜???뺣낫瑜??뺤씤?????놁뒿?덈떎.")
        return {
            "provider_user_id": provider_user_id,
            "email": email or f"naver_{provider_user_id}@social.local",
            "display_name": display_name or "Naver User",
        }

    if config["provider"] == "github":
        github_headers = headers | {"User-Agent": "Sketch-to-Cloud"}
        response = _request_json("https://api.github.com/user", headers=github_headers)
        if not isinstance(response, dict):
            raise HTTPException(status_code=502, detail="GitHub ?ъ슜???뺣낫瑜??뺤씤?????놁뒿?덈떎.")
        provider_user_id = _as_clean_text(response.get("id", ""))
        email = _as_clean_text(response.get("email", ""))
        display_name = (
            _as_clean_text(response.get("name", ""))
            or _as_clean_text(response.get("login", ""))
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
                email = _as_clean_text(primary_email or fallback_email or "")
        if not provider_user_id:
            raise HTTPException(status_code=502, detail="GitHub ?ъ슜???뺣낫瑜??뺤씤?????놁뒿?덈떎.")
        return {
            "provider_user_id": provider_user_id,
            "email": email or f"github_{provider_user_id}@social.local",
            "display_name": display_name or "GitHub User",
        }

    response = _request_json("https://kapi.kakao.com/v2/user/me", headers=headers)
    kakao_account = response.get("kakao_account", {}) if isinstance(response, dict) else {}
    profile = kakao_account.get("profile", {}) if isinstance(kakao_account, dict) else {}
    provider_user_id = _as_clean_text(response.get("id", ""))
    email = _as_clean_text(kakao_account.get("email", ""))
    display_name = (
        _as_clean_text(profile.get("nickname", ""))
        or _as_clean_text(profile.get("name", ""))
        or email.split("@")[0]
    )
    if not provider_user_id:
        raise HTTPException(status_code=502, detail="移댁뭅???ъ슜???뺣낫瑜??뺤씤?????놁뒿?덈떎.")
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
        raise HTTPException(status_code=409, detail="?대? ?ъ슜 以묒씤 ?대찓?쇱엯?덈떎. 湲곗〈 怨꾩젙?쇰줈 濡쒓렇?명빐 二쇱꽭??")

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


def _build_deploy_trust_policy_json(principal_arn: str | None, external_id: str | None) -> str:
    if not principal_arn:
        return ""
    principal = principal_arn
    statement: dict[str, object] = {
        "Effect": "Allow",
        "Principal": {"AWS": principal},
        "Action": "sts:AssumeRole",
    }
    if external_id:
        statement["Condition"] = {"StringEquals": {"sts:ExternalId": external_id}}
    policy = {"Version": "2012-10-17", "Statement": [statement]}
    return json.dumps(policy, ensure_ascii=False, indent=2)


def _normalize_principal_arn_for_trust(raw_arn: str) -> str:
    arn = raw_arn.strip()
    # STS assumed role -> IAM role ARN
    assumed_match = re.match(r"^arn:aws:sts::(\d+):assumed-role/([^/]+)/[^/]+$", arn)
    if assumed_match:
        account_id = assumed_match.group(1)
        role_name = assumed_match.group(2)
        return f"arn:aws:iam::{account_id}:role/{role_name}"
    return arn


def _extract_account_id_from_iam_arn(raw_arn: str | None) -> str | None:
    if not raw_arn:
        return None
    matched = re.match(r"^arn:aws:iam::(\d+):", raw_arn.strip())
    if not matched:
        return None
    return matched.group(1)


@router.post("/api/auth/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    existing_email = db.scalars(select(User).where(User.email == payload.email).limit(1)).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="?대? ?ъ슜 以묒씤 ?대찓?쇱엯?덈떎.")

    existing_login = db.scalars(select(User).where(User.login_id == payload.loginId).limit(1)).first()
    if existing_login:
        raise HTTPException(status_code=409, detail="?대? ?ъ슜 以묒씤 ?꾩씠?붿엯?덈떎.")

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
        raise HTTPException(status_code=401, detail="?꾩씠???먮뒗 鍮꾨?踰덊샇媛 ?쇱튂?섏? ?딆뒿?덈떎.")

    if not user.password_hash or user.password_hash != hash_text(payload.password):
        raise HTTPException(status_code=401, detail="?꾩씠???먮뒗 鍮꾨?踰덊샇媛 ?쇱튂?섏? ?딆뒿?덈떎.")

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
        raise HTTPException(status_code=409, detail="?뚯뀥 怨꾩젙 媛??泥섎━ 以?以묐났 ?곗씠?곌? 諛쒖깮?덉뒿?덈떎.")
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Social signup database error for provider=%s", payload.provider)
        raise HTTPException(status_code=500, detail="?뚯뀥 怨꾩젙 媛??泥섎━ 以??곗씠????μ뿉 ?ㅽ뙣?덉뒿?덈떎.")


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
        return _redirect_social_result(error=f"{normalized_provider} 濡쒓렇?몄뿉 ?ㅽ뙣?덉뒿?덈떎: {error}")

    if not code or not state:
        return _redirect_social_result(error="?뚯뀥 濡쒓렇???묐떟???꾩슂??媛믪씠 ?꾨씫?섏뿀?듬땲??")

    _prune_social_states()
    stored_provider, expires_at = SOCIAL_STATE_STORE.pop(state, ("", datetime.now(timezone.utc)))
    if stored_provider != normalized_provider or expires_at <= datetime.now(timezone.utc):
        return _redirect_social_result(error="?뚯뀥 濡쒓렇???붿껌??留뚮즺?섏뿀嫄곕굹 ?щ컮瑜댁? ?딆뒿?덈떎.")

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
        if normalized_provider == "github":
            put_github_access_token(db, login_response.user.userId, provider_access_token)
            db.commit()
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
        return _redirect_social_result(error="?뚯뀥 濡쒓렇??怨꾩젙 ?곌껐 以?以묐났 ?곗씠?곌? 諛쒖깮?덉뒿?덈떎. ?ㅼ떆 ?쒕룄??二쇱꽭??")
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Social login database error for provider=%s", normalized_provider)
        return _redirect_social_result(error="?뚯뀥 濡쒓렇??以??곗씠????μ뿉 ?ㅽ뙣?덉뒿?덈떎. ?좎떆 ???ㅼ떆 ?쒕룄??二쇱꽭??")
    except Exception:
        db.rollback()
        logger.exception("Unexpected social login error for provider=%s", normalized_provider)
        return _redirect_social_result(error="?뚯뀥 濡쒓렇??泥섎━ 以??????녿뒗 ?ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.")

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


@router.get("/api/users/aws-deploy-config", response_model=AwsDeployConfigResponse)
def get_aws_deploy_config(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AwsDeployConfigResponse:
    try:
        config = db.scalars(select(UserDeployConfig).where(UserDeployConfig.user_id == user.id).limit(1)).first()
    except ProgrammingError:
        db.rollback()
        return AwsDeployConfigResponse(configured=False)
    if not config:
        return AwsDeployConfigResponse(configured=False)
    return AwsDeployConfigResponse(
        configured=True,
        roleArn=config.role_arn,
        roleExternalId=config.role_external_id,
        roleSessionName=config.role_session_name,
    )


@router.put("/api/users/aws-deploy-config", response_model=AwsDeployConfigResponse)
def upsert_aws_deploy_config(
    payload: AwsDeployConfigRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AwsDeployConfigResponse:
    try:
        config = db.scalars(select(UserDeployConfig).where(UserDeployConfig.user_id == user.id).limit(1)).first()
    except ProgrammingError as e:
        db.rollback()
        raise HTTPException(status_code=503, detail="aws deploy config table is not ready. run alembic upgrade head") from e
    if config:
        config.role_arn = payload.roleArn.strip()
        config.role_external_id = payload.roleExternalId.strip() if payload.roleExternalId else None
        config.role_session_name = payload.roleSessionName.strip() if payload.roleSessionName else None
        config.updated_at = datetime.now(timezone.utc)
    else:
        config = UserDeployConfig(
            user_id=user.id,
            role_arn=payload.roleArn.strip(),
            role_external_id=payload.roleExternalId.strip() if payload.roleExternalId else None,
            role_session_name=payload.roleSessionName.strip() if payload.roleSessionName else None,
        )
        db.add(config)

    db.commit()
    return AwsDeployConfigResponse(
        configured=True,
        roleArn=config.role_arn,
        roleExternalId=config.role_external_id,
        roleSessionName=config.role_session_name,
    )


@router.get("/api/users/aws-deploy-guide", response_model=AwsDeployGuideResponse)
def get_aws_deploy_guide(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AwsDeployGuideResponse:
    try:
        config = db.scalars(select(UserDeployConfig).where(UserDeployConfig.user_id == user.id).limit(1)).first()
    except ProgrammingError:
        db.rollback()
        config = None

    configured_role_arn = config.role_arn if config else None
    principal_arn = os.getenv("DEPLOY_ASSUME_PRINCIPAL_ARN", "").strip() or None
    if not principal_arn:
        region = os.getenv("DEFAULT_DEPLOY_REGION", "ap-northeast-2").strip() or "ap-northeast-2"
        try:
            sts = boto3.client("sts", region_name=region)
            caller_arn = str(sts.get_caller_identity().get("Arn", "")).strip()
            principal_arn = _normalize_principal_arn_for_trust(caller_arn) if caller_arn else None
        except (BotoCoreError, ClientError):
            principal_arn = None
    if not principal_arn:
        account_id = _extract_account_id_from_iam_arn(configured_role_arn)
        if account_id:
            principal_arn = f"arn:aws:iam::{account_id}:root"
    external_id = os.getenv("DEPLOY_ASSUME_ROLE_EXTERNAL_ID", "").strip() or None
    role_name = os.getenv("DEPLOY_SUGGESTED_ROLE_NAME", "stc-deploy-role").strip() or "stc-deploy-role"
    policy_arn = os.getenv("DEPLOY_RECOMMENDED_POLICY_ARN", "arn:aws:iam::aws:policy/AdministratorAccess").strip()
    region = os.getenv("DEFAULT_DEPLOY_REGION", "ap-northeast-2").strip() or "ap-northeast-2"

    return AwsDeployGuideResponse(
        configured=bool(config and config.role_arn),
        requiredPrincipalArn=principal_arn,
        requiredExternalId=external_id,
        suggestedRoleName=role_name,
        recommendedPolicyArn=policy_arn,
        trustPolicyJson=_build_deploy_trust_policy_json(principal_arn, external_id),
        iamRoleCreateUrl=f"https://console.aws.amazon.com/iam/home?region={region}#/roles/create",
        iamRolesListUrl=f"https://console.aws.amazon.com/iam/home?region={region}#/roles",
    )


@router.delete("/api/users/aws-deploy-config", response_model=AwsDeployConfigResponse)
def delete_aws_deploy_config(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AwsDeployConfigResponse:
    try:
        config = db.scalars(select(UserDeployConfig).where(UserDeployConfig.user_id == user.id).limit(1)).first()
    except ProgrammingError:
        db.rollback()
        return AwsDeployConfigResponse(configured=False)
    if config:
        db.delete(config)
        db.commit()
    return AwsDeployConfigResponse(configured=False)
