from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


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
    memberships: list[MembershipSummary]
