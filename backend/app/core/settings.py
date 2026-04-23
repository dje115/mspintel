from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "mspintel"
    environment: str = "development"
    app_version: str = Field(default="1.2", validation_alias="MSPINTEL_APP_VERSION")

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
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 7

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
