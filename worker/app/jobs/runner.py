from datetime import UTC, datetime

from app.core.settings import get_settings


def run_placeholder_jobs() -> None:
    settings = get_settings()
    print(
        f"[{datetime.now(UTC).isoformat()}] {settings.project_name} worker poll "
        f"(billing_provider={settings.billing_provider}, redis={settings.redis_url})"
    )
