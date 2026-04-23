from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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
    totp_code: str | None = Field(default=None, max_length=32)
    recovery_code: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def exactly_one_second_factor(self) -> "PlatformMfaLoginRequest":
        t = (self.totp_code or "").strip()
        r = (self.recovery_code or "").strip()
        if bool(t) == bool(r):
            raise ValueError("Provide exactly one of totp_code or recovery_code")
        self.totp_code = t if t else None
        self.recovery_code = r if r else None
        return self


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
    recovery_codes_unused: int = 0


class RecoveryCodesGenerateResponse(BaseModel):
    codes: list[str]
    batch_id: UUID
