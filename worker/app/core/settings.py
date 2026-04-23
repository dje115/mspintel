from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "mspintel"
    environment: str = "development"
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+psycopg://mspintel:mspintel@postgres:5432/mspintel"
    worker_poll_seconds: int = 5

    billing_provider: str = "stripe"


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
