from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    session_id: UUID


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class LogoutAllRequest(BaseModel):
    """When ``keep_refresh_token`` is set to the caller's current refresh token, other sessions are revoked."""

    keep_refresh_token: str | None = None


class UserSessionResponse(BaseModel):
    id: UUID
    auth_mode: Literal["tenant", "platform"] = "tenant"
    ip_address: str | None
    device_label: str | None
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    revoked_at: datetime | None
    is_current: bool = False


class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    tenant_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MembershipSummary(BaseModel):
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    role_code: str


class UserMeResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str
    is_platform_admin: bool
    auth_mode: Literal["tenant", "platform"] = "tenant"
    memberships: list[MembershipSummary]
