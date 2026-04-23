from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "mspintel"
    environment: str = "development"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = "postgresql+psycopg://mspintel:mspintel@postgres:5432/mspintel"
    redis_url: str = "redis://redis:6379/0"

    # SaaS multi-tenant identity and context defaults
    require_tenant_context: bool = False
    platform_admin_email_domain: str = "mspintel.local"

    # Future provider and security settings
    ai_provider_default: str = "openai"
    ai_provider_api_key: str = ""
    integration_encryption_key: str = "change-me"

    # Future billing/subscription provider settings
    billing_provider: str = "stripe"
    billing_provider_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
