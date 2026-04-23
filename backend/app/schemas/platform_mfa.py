from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PlatformLoginResponse(BaseModel):
    """Result of password-only ``POST /auth/platform/login`` (may require a second step)."""

    outcome: Literal["authenticated", "mfa_challenge", "mfa_enrollment_setup"]
    access_token: str | None = None
    refresh_token: str | None = None
    session_id: UUID | None = None
    token_type: str = "bearer"
    mfa_challenge_token: str | None = None
    enrollment_setup_token: str | None = None


class PlatformMfaLoginRequest(BaseModel):
    mfa_challenge_token: str = Field(min_length=10)
    totp_code: str = Field(min_length=4, max_length=12)


class TotpEnrollmentStartResponse(BaseModel):
    method_id: UUID
    otpauth_uri: str


class TotpEnrollmentConfirmRequest(BaseModel):
    method_id: UUID
    totp_code: str = Field(min_length=4, max_length=12)


class TotpDisableRequest(BaseModel):
    totp_code: str = Field(min_length=4, max_length=12)


class PlatformMfaStatusResponse(BaseModel):
    totp_enabled: bool
    totp_pending: bool
    platform_mfa_required: bool
    pending_method_id: UUID | None = None
