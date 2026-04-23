"""Redis-backed fixed-window rate limits for platform password / MFA endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

import redis

from app.core.settings import get_settings

_log = logging.getLogger("mspintel.platform_ratelimit")


def _redis_client() -> redis.Redis | None:
    settings = get_settings()
    if not settings.platform_login_ratelimit_enabled:
        return None
    try:
        return redis.Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception as exc:  # pragma: no cover - defensive
        _log.warning("platform_ratelimit_redis_unavailable", exc_info=exc)
        return None


def _incr_limited(key: str, window_seconds: int, max_events: int) -> bool:
    """Return True if under or at limit after increment, False if over limit."""
    r = _redis_client()
    if r is None:
        return True
    try:
        n = int(r.incr(key))
        if n == 1:
            r.expire(key, window_seconds)
        return n <= max_events
    except Exception as exc:  # pragma: no cover
        _log.warning("platform_ratelimit_redis_error", exc_info=exc)
        return True


def increment_platform_password_login_failures(ip: str | None) -> bool:
    """Increment failed password-step counter for ``ip``.

    Returns ``True`` if the client is still under the configured cap (caller should return a
    normal **401**). Returns ``False`` if the cap was exceeded after this increment (caller
    should return **429** and emit ``platform.login.rate_limited``).
    """
    settings = get_settings()
    ident = ip or "unknown"
    key = f"mspintel:rl:platform:pw:{ident}"
    return _incr_limited(key, settings.platform_login_password_window_seconds, settings.platform_login_password_max_attempts)


def increment_platform_mfa_login_failures(ip: str | None, user_id: UUID) -> bool:
    """Increment failed MFA-step counter for ``ip`` + ``user_id``.

    Return semantics match :func:`increment_platform_password_login_failures`.
    """
    settings = get_settings()
    ident = ip or "unknown"
    key = f"mspintel:rl:platform:mfa:{ident}:{user_id}"
    return _incr_limited(key, settings.platform_login_mfa_window_seconds, settings.platform_login_mfa_max_attempts)
