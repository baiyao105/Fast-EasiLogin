from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    details: Any = None


class ApiEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ApiError | None = None
    request_id: str


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class DashboardAccount(BaseModel):
    user_id: str
    phone: str | None = None
    nickname: str
    real_name: str | None = None
    avatar_url: str
    active: bool
    last_login_at: datetime | None = None
    login_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AccountVerifyRequest(BaseModel):
    account: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=512)


class UpstreamUserProfile(BaseModel):
    user_id: str
    phone: str | None = None
    nickname: str = ""
    real_name: str | None = None
    avatar_url: str = ""


class AccountVerification(BaseModel):
    verification_token: str
    expires_at: datetime
    profile: UpstreamUserProfile


class AccountCreateRequest(BaseModel):
    verification_token: str = Field(min_length=1)


class AccountPatchRequest(BaseModel):
    active: bool | None = None


class DashboardLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


class AuthStatus(BaseModel):
    authenticated: bool
    password_required: bool


class SettingsPatch(BaseModel):
    network: dict[str, Any] | None = None
    runtime: dict[str, Any] | None = None
    authentication: dict[str, Any] | None = None
    encryption: dict[str, Any] | None = None


class ServiceCommand(BaseModel):
    reason: str | None = None


class EncryptionRotateRequest(BaseModel):
    key_source: Literal["environment", "dpapi"]


class LoginEvent(BaseModel):
    id: int
    user_id: str | None = None
    username: str
    status: str
    error_code: str | None = None
    ip_address: str
    created_at: datetime


class LoginEventSummary(BaseModel):
    counts: dict[str, int]
