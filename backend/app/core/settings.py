from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "mspintel"
    environment: str = "development"
    app_version: str = Field(default="2.3.0", validation_alias="MSPINTEL_APP_VERSION")

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @model_validator(mode="after")
    def _ensure_cors_origins_non_empty(self) -> "Settings":
        """Mis-set ``BACKEND_CORS_ORIGINS`` in .env often parses as []; that strips CORS headers entirely."""
        if not self.backend_cors_origins:
            self.backend_cors_origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        return self

    database_url: str = "postgresql+psycopg://mspintel:mspintel@postgres:5432/mspintel"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    # Tenant workspace sessions (JWT ``am=tenant``)
    tenant_access_token_expire_minutes: int = Field(
        default=30,
        validation_alias="TENANT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    tenant_refresh_token_expire_days: int = Field(
        default=7,
        validation_alias="TENANT_REFRESH_TOKEN_EXPIRE_DAYS",
    )
    # Platform console sessions (JWT ``am=platform``) — shorter defaults by design
    platform_access_token_expire_minutes: int = Field(
        default=15,
        validation_alias="PLATFORM_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    platform_refresh_token_expire_days: int = Field(
        default=3,
        validation_alias="PLATFORM_REFRESH_TOKEN_EXPIRE_DAYS",
    )

    # Platform TOTP MFA (operator accounts only; see docs/PLATFORM_MFA.md)
    platform_mfa_required: bool = Field(default=False, validation_alias="PLATFORM_MFA_REQUIRED")
    mfa_totp_encryption_key: str = Field(
        default="sEPh09o3P1QLJECURZ1PrQbVIv540e3eec0lgsBvxeA=",
        validation_alias="MFA_TOTP_ENCRYPTION_KEY",
        description="Fernet key (44 url-safe base64 chars). Override in production.",
    )
    mfa_challenge_ttl_minutes: int = Field(default=5, validation_alias="MFA_CHALLENGE_TTL_MINUTES")
    mfa_enrollment_setup_ttl_minutes: int = Field(
        default=15,
        validation_alias="MFA_ENROLLMENT_SETUP_TTL_MINUTES",
    )
    mfa_recovery_code_pepper: str = Field(
        default="dev-mfa-recovery-pepper-min-sixteen",
        validation_alias="MFA_RECOVERY_CODE_PEPPER",
        description="HMAC pepper for hashing platform recovery codes at rest.",
    )

    platform_login_ratelimit_enabled: bool = Field(
        default=True,
        validation_alias="PLATFORM_LOGIN_RATELIMIT_ENABLED",
    )
    platform_login_password_max_attempts: int = Field(
        default=30,
        ge=1,
        validation_alias="PLATFORM_LOGIN_PASSWORD_MAX_ATTEMPTS",
    )
    platform_login_password_window_seconds: int = Field(
        default=900,
        ge=30,
        validation_alias="PLATFORM_LOGIN_PASSWORD_WINDOW_SECONDS",
    )
    platform_login_mfa_max_attempts: int = Field(
        default=40,
        ge=1,
        validation_alias="PLATFORM_LOGIN_MFA_MAX_ATTEMPTS",
    )
    platform_login_mfa_window_seconds: int = Field(
        default=900,
        ge=30,
        validation_alias="PLATFORM_LOGIN_MFA_WINDOW_SECONDS",
    )

    @field_validator("mfa_totp_encryption_key")
    @classmethod
    def _mfa_totp_key_must_be_valid_fernet(cls, v: str) -> str:
        """Reject misconfigured keys early so TOTP secrets are never written with a broken cipher."""
        from cryptography.fernet import Fernet

        s = (v or "").strip()
        if not s:
            raise ValueError("MFA_TOTP_ENCRYPTION_KEY must not be empty")
        try:
            Fernet(s.encode("utf-8"))
        except Exception as exc:
            raise ValueError(
                "MFA_TOTP_ENCRYPTION_KEY must be a url-safe base64-encoded 32-byte Fernet key "
                "(generate with cryptography.fernet.Fernet.generate_key())"
            ) from exc
        return s

    @field_validator("mfa_recovery_code_pepper")
    @classmethod
    def _mfa_recovery_pepper_min_length(cls, v: str) -> str:
        s = (v or "").strip()
        if len(s) < 16:
            raise ValueError("MFA_RECOVERY_CODE_PEPPER must be at least 16 characters")
        return s

    invitation_ttl_hours: int = 72
    frontend_app_url: str = "http://localhost:5173"
    expose_invitation_token_in_response: bool = False

    mail_from_email: str = "noreply@mspintel.local"
    mail_smtp_host: str = "mailpit"
    mail_smtp_port: int = 1025
    mail_smtp_username: str = ""
    mail_smtp_password: str = ""
    mail_use_tls: bool = False

    require_tenant_context: bool = False

    ai_provider_default: str = "openai"
    ai_provider_api_key: str = ""
    integration_encryption_key: str = "change-me"

    billing_provider: str = "stripe"
    billing_provider_api_key: str = ""

    seed_platform_admin_email: str = "admin@mspintel.example.com"
    seed_platform_admin_password: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()
