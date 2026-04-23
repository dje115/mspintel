import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.settings import get_settings

settings = get_settings()

# JWT ``am`` claim: tenant app vs platform console (same user store, scoped tokens).
AUTH_MODE_TENANT = "tenant"
AUTH_MODE_PLATFORM = "platform"


def _pbkdf2_hash(password: str, salt: bytes, rounds: int = 310_000) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        scheme, rounds_str, salt_b64, hash_b64 = hashed_password.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        rounds = int(rounds_str)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(hash_b64.encode("utf-8"))
        computed = _pbkdf2_hash(plain_password, salt, rounds)
        return hmac.compare_digest(expected, computed)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    rounds = 310_000
    salt = secrets.token_bytes(16)
    digest = _pbkdf2_hash(password, salt, rounds)
    return "pbkdf2_sha256${}${}${}".format(
        rounds,
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(digest).decode("utf-8"),
    )


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    *,
    session_id: uuid.UUID | None = None,
    auth_mode: str = AUTH_MODE_TENANT,
) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "typ": "access", "am": auth_mode}
    if session_id is not None:
        to_encode["sid"] = str(session_id)
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
    *,
    auth_mode: str = AUTH_MODE_TENANT,
) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_refresh_token_expire_minutes))
    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "typ": "refresh",
        "jti": secrets.token_hex(12),
        "am": auth_mode,
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def decode_access_token(token: str) -> str | None:
    payload = decode_access_token_payload(token)
    if not payload:
        return None
    return str(payload.get("sub")) if payload.get("sub") else None


def decode_access_token_payload(token: str) -> dict[str, Any] | None:
    payload = decode_token(token)
    if not payload or payload.get("typ") != "access":
        return None
    return payload


def auth_mode_from_payload(payload: dict[str, Any] | None) -> str:
    """Return ``tenant`` or ``platform`` from JWT payload; missing ``am`` defaults to tenant (legacy tokens)."""
    if not payload:
        return AUTH_MODE_TENANT
    raw = payload.get("am")
    if raw == AUTH_MODE_PLATFORM:
        return AUTH_MODE_PLATFORM
    return AUTH_MODE_TENANT


def auth_mode_from_refresh_payload(payload: dict[str, Any] | None) -> str:
    if not payload:
        return AUTH_MODE_TENANT
    raw = payload.get("am")
    if raw == AUTH_MODE_PLATFORM:
        return AUTH_MODE_PLATFORM
    return AUTH_MODE_TENANT


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
