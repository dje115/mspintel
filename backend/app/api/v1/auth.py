import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.access import BearerIdentity, get_bearer_identity
from app.api.deps.db import get_db
from app.core.request_meta import client_ip, device_label_from_user_agent, user_agent
from app.core.security import AUTH_MODE_PLATFORM, AUTH_MODE_TENANT
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MembershipSummary,
    RefreshRequest,
    SignupRequest,
    TokenPairResponse,
    UserMeResponse,
    UserSessionResponse,
)
from app.models.entities import Role, Tenant, TenantMembership
from app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
_log = logging.getLogger("mspintel.auth")


def _meta(request: Request) -> tuple[str | None, str | None, str | None]:
    ip = client_ip(request)
    ua = user_agent(request)
    return ip, ua, device_label_from_user_agent(ua)


def _audit_tenant_for_revoke(
    db: Session, user_id: UUID, auth_mode: str, x_tenant_id: UUID | None
) -> UUID | None:
    if auth_mode == AUTH_MODE_PLATFORM:
        return None
    base = select(TenantMembership).where(
        TenantMembership.user_id == user_id,
        TenantMembership.status == "active",
    )
    if x_tenant_id is not None:
        m = db.scalars(base.where(TenantMembership.tenant_id == x_tenant_id)).first()
        if m:
            return x_tenant_id
    m = db.scalars(base).first()
    return m.tenant_id if m else None


@router.post("/signup", response_model=TokenPairResponse)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)) -> TokenPairResponse:
    service = AuthService(db)
    try:
        user = service.signup(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ip, ua, label = _meta(request)
    return service.issue_token_pair(
        user, ip_address=ip, user_agent=ua, device_label=label, auth_mode=AUTH_MODE_TENANT
    )


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPairResponse:
    service = AuthService(db)
    user = service.authenticate(payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrators must sign in via the platform console.",
        )
    ip, ua, label = _meta(request)
    return service.issue_token_pair(
        user, ip_address=ip, user_agent=ua, device_label=label, auth_mode=AUTH_MODE_TENANT
    )


@router.post("/platform/login", response_model=TokenPairResponse)
def platform_login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPairResponse:
    service = AuthService(db)
    user = service.authenticate(payload)
    if not user:
        _log.info("platform_login_failed", extra={"reason": "invalid_credentials"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to sign in")
    if not user.is_platform_admin:
        _log.info("platform_login_denied", extra={"reason": "not_platform_admin", "user_id": str(user.id)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to sign in")
    _log.info("platform_login_ok", extra={"user_id": str(user.id)})
    ip, ua, label = _meta(request)
    return service.issue_token_pair(
        user, ip_address=ip, user_agent=ua, device_label=label, auth_mode=AUTH_MODE_PLATFORM
    )


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenPairResponse:
    try:
        ip, ua, label = _meta(request)
        return AuthService(db).refresh(payload, ip_address=ip, user_agent=ua, device_label=label)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    AuthService(db).logout(payload.refresh_token)
    return {"status": "ok"}


@router.post("/logout-all")
async def logout_all(
    request: Request,
    identity: BearerIdentity = Depends(get_bearer_identity),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    keep_refresh_token: str | None = None
    body = await request.body()
    if body.strip():
        try:
            raw = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body"
            ) from exc
        if isinstance(raw, dict) and raw.get("keep_refresh_token"):
            keep_refresh_token = str(raw["keep_refresh_token"])
    try:
        count = AuthService(db).logout_all(identity.user.id, keep_refresh_token=keep_refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"revoked_sessions": count}


@router.get("/sessions", response_model=list[UserSessionResponse])
def list_sessions(
    identity: BearerIdentity = Depends(get_bearer_identity), db: Session = Depends(get_db)
):
    rows = AuthService(db).sessions.list_for_user(identity.user.id)
    return [
        UserSessionResponse(
            id=s.id,
            ip_address=s.ip_address,
            device_label=s.device_label,
            user_agent=s.user_agent,
            created_at=s.created_at,
            last_used_at=s.last_used_at,
            expires_at=s.expires_at,
            revoked_at=s.revoked_at,
            is_current=identity.current_session_id is not None and s.id == identity.current_session_id,
        )
        for s in rows
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: UUID,
    identity: BearerIdentity = Depends(get_bearer_identity),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-Id"),
    db: Session = Depends(get_db),
):
    if identity.current_session_id is not None and session_id == identity.current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use POST /api/v1/auth/logout with your refresh token to end this session",
        )
    audit_tenant = _audit_tenant_for_revoke(db, identity.user.id, identity.auth_mode, x_tenant_id)
    try:
        changed = AuthService(db).revoke_session_for_user(
            identity.user.id,
            session_id,
            tenant_id_for_audit=audit_tenant,
            actor_user_id=identity.user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"revoked": changed}


@router.get("/me", response_model=UserMeResponse)
def me(identity: BearerIdentity = Depends(get_bearer_identity), db: Session = Depends(get_db)) -> UserMeResponse:
    rows = db.execute(
        select(TenantMembership, Tenant, Role)
        .join(Tenant, TenantMembership.tenant_id == Tenant.id)
        .join(Role, TenantMembership.role_id == Role.id)
        .where(TenantMembership.user_id == identity.user.id, TenantMembership.status == "active")
    ).all()

    memberships = [
        MembershipSummary(
            tenant_id=membership.tenant_id,
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
            role_code=role.code,
        )
        for membership, tenant, role in rows
    ]

    auth_mode_literal = "platform" if identity.auth_mode == AUTH_MODE_PLATFORM else "tenant"

    return UserMeResponse(
        user_id=identity.user.id,
        email=identity.user.email,
        full_name=identity.user.full_name,
        is_platform_admin=identity.user.is_platform_admin,
        auth_mode=auth_mode_literal,
        memberships=memberships,
    )
