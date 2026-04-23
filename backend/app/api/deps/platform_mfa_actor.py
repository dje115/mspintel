"""Bearer identity for TOTP enrolment: platform access JWT or short-lived ``mfa_enroll`` setup token."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps.db import get_db
from app.core.security import (
    AUTH_MODE_PLATFORM,
    MFA_ENROLL_TYP,
    auth_mode_from_payload,
    decode_token,
)
from app.models.entities import User

_security = HTTPBearer(auto_error=False)


def get_platform_mfa_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    payload = decode_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")
    typ = payload.get("typ")
    user = db.get(User, UUID(str(payload["sub"])))
    if not user or not user.is_platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if typ == MFA_ENROLL_TYP:
        return user
    if typ == "access" and auth_mode_from_payload(payload) == AUTH_MODE_PLATFORM:
        return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported token for MFA enrolment")
