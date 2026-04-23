from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, get_access_context
from app.api.deps.db import get_db
from app.core.security import create_access_token
from app.models.entities import Role, Tenant, TenantMembership
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MembershipSummary,
    RefreshRequest,
    SignupRequest,
    TokenPairResponse,
    UserMeResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", response_model=TokenPairResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    service = AuthService(db)
    try:
        user = service.signup(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return service.issue_token_pair(user)


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    service = AuthService(db)
    user = service.authenticate(payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return service.issue_token_pair(user)


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    try:
        return AuthService(db).refresh(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    AuthService(db).logout(payload.refresh_token)
    return {"status": "ok"}


@router.post("/logout-all")
def logout_all(ctx: AccessContext = Depends(get_access_context), db: Session = Depends(get_db)) -> dict[str, int]:
    count = AuthService(db).logout_all(ctx.user.id)
    return {"revoked_sessions": count}


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
