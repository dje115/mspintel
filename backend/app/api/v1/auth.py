import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, get_access_context
from app.api.deps.db import get_db
from app.core.request_meta import client_ip, device_label_from_user_agent, user_agent
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


def _meta(request: Request) -> tuple[str | None, str | None, str | None]:
    ip = client_ip(request)
    ua = user_agent(request)
    return ip, ua, device_label_from_user_agent(ua)


@router.post("/signup", response_model=TokenPairResponse)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)) -> TokenPairResponse:
    service = AuthService(db)
    try:
        user = service.signup(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ip, ua, label = _meta(request)
    return service.issue_token_pair(user, ip_address=ip, user_agent=ua, device_label=label)


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPairResponse:
    service = AuthService(db)
    user = service.authenticate(payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    ip, ua, label = _meta(request)
    return service.issue_token_pair(user, ip_address=ip, user_agent=ua, device_label=label)


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
    ctx: AccessContext = Depends(get_access_context),
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
        count = AuthService(db).logout_all(ctx.user.id, keep_refresh_token=keep_refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"revoked_sessions": count}


@router.get("/sessions", response_model=list[UserSessionResponse])
def list_sessions(ctx: AccessContext = Depends(get_access_context), db: Session = Depends(get_db)):
    rows = AuthService(db).sessions.list_for_user(ctx.user.id)
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
            is_current=ctx.current_session_id is not None and s.id == ctx.current_session_id,
        )
        for s in rows
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: UUID,
    ctx: AccessContext = Depends(get_access_context),
    db: Session = Depends(get_db),
):
    if ctx.current_session_id is not None and session_id == ctx.current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use POST /api/v1/auth/logout with your refresh token to end this session",
        )
    try:
        changed = AuthService(db).revoke_session_for_user(
            ctx.user.id,
            session_id,
            tenant_id_for_audit=ctx.tenant.id,
            actor_user_id=ctx.user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"revoked": changed}


@router.get("/me", response_model=UserMeResponse)
def me(ctx: AccessContext = Depends(get_access_context), db: Session = Depends(get_db)) -> UserMeResponse:
    rows = db.execute(
        select(TenantMembership, Tenant, Role)
        .join(Tenant, TenantMembership.tenant_id == Tenant.id)
        .join(Role, TenantMembership.role_id == Role.id)
        .where(TenantMembership.user_id == ctx.user.id, TenantMembership.status == "active")
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

    return UserMeResponse(
        user_id=ctx.user.id,
        email=ctx.user.email,
        full_name=ctx.user.full_name,
        is_platform_admin=ctx.user.is_platform_admin,
        memberships=memberships,
    )
