from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import CONTRACT_VERSION
from app.core.validators import validate_login_id, validate_password_rules


class RegisterRequest(BaseModel):
    loginId: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    displayName: str = Field(min_length=1, max_length=100)

    @field_validator("loginId")
    @classmethod
    def validate_register_login_id(cls, value: str) -> str:
        return validate_login_id(value)

    @field_validator("password")
    @classmethod
    def validate_register_password(cls, value: str) -> str:
        return validate_password_rules(value)


class RegisterResponse(BaseModel):
    userId: str
    loginId: str
    email: str
    displayName: str
    isActive: bool
    role: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class LoginRequest(BaseModel):
    loginId: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


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


class SocialSignupCompleteRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=30)
    providerUserId: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    displayName: str = Field(min_length=1, max_length=100)


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


class AwsDeployConfigRequest(BaseModel):
    roleArn: str = Field(min_length=20, max_length=500)
    roleExternalId: str | None = Field(default=None, min_length=2, max_length=200)
    roleSessionName: str | None = Field(default=None, min_length=2, max_length=64)


class AwsDeployConfigResponse(BaseModel):
    configured: bool
    roleArn: str | None = None
    roleExternalId: str | None = None
    roleSessionName: str | None = None
    contractVersion: Literal["v2"] = CONTRACT_VERSION
