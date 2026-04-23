"""JWT lifetimes for tenant vs platform sessions (single source of truth).

Call :func:`access_refresh_deltas` from :class:`app.services.auth.AuthService` when issuing
or rotating tokens so platform and tenant policies stay explicit and centralized.
"""

from datetime import timedelta

from app.core.security import AUTH_MODE_PLATFORM, AUTH_MODE_TENANT
from app.core.settings import get_settings


def access_refresh_deltas(auth_mode: str) -> tuple[timedelta, timedelta]:
    """Return ``(access_token_ttl, refresh_token_ttl)`` for the given JWT ``auth_mode``."""
    s = get_settings()
    if auth_mode == AUTH_MODE_PLATFORM:
        return (
            timedelta(minutes=s.platform_access_token_expire_minutes),
            timedelta(days=s.platform_refresh_token_expire_days),
        )
    return (
        timedelta(minutes=s.tenant_access_token_expire_minutes),
        timedelta(days=s.tenant_refresh_token_expire_days),
    )


def normalized_session_auth_mode(value: str | None) -> str:
    """DB ``auth_mode`` for sessions; legacy null/unknown maps to tenant."""
    if value == AUTH_MODE_PLATFORM:
        return AUTH_MODE_PLATFORM
    return AUTH_MODE_TENANT
