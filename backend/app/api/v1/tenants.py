from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, get_access_context, get_optional_user, require_permission
from app.api.deps.db import get_db
from app.models.entities import Role, TenantMembership, User
from app.schemas.invitation import InvitationAcceptRequest, InvitationAcceptResponse, InvitationCreateRequest, InvitationResponse
from app.schemas.tenant import (
    CurrentTenantResponse,
    OnboardingStateResponse,
    OnboardingStateUpdate,
    SubscriptionSummary,
    TenantMemberResponse,
)
from app.services.invitation import InvitationService
from app.services.tenant import TenantService

router = APIRouter(prefix="/api/v1/tenants/current", tags=["tenants"])


@router.get("", response_model=CurrentTenantResponse)
def current_tenant(ctx: AccessContext = Depends(get_access_context)) -> CurrentTenantResponse:
    return CurrentTenantResponse(
        tenant_id=ctx.tenant.id,
        tenant_name=ctx.tenant.name,
        tenant_slug=ctx.tenant.slug,
        role_code=ctx.role_code,
    )


@router.get("/members", response_model=list[TenantMemberResponse])
def members(
    ctx: AccessContext = Depends(require_permission("membership:read")),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(TenantMembership, User, Role)
        .join(User, TenantMembership.user_id == User.id)
        .join(Role, TenantMembership.role_id == Role.id)
        .where(TenantMembership.tenant_id == ctx.tenant.id)
    ).all()
    return [
        TenantMemberResponse(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            role_code=role.code,
            status=membership.status,
        )
        for membership, user, role in rows
    ]


@router.get("/invitations", response_model=list[InvitationResponse])
def invitations(
    ctx: AccessContext = Depends(require_permission("invitation:read")),
    db: Session = Depends(get_db),
):
    return InvitationService(db).list_for_tenant(ctx.tenant.id)


@router.post("/invitations", response_model=InvitationResponse)
def create_invitation(
    payload: InvitationCreateRequest,
    ctx: AccessContext = Depends(require_permission("invitation:write")),
    db: Session = Depends(get_db),
):
    return InvitationService(db).create_invitation(ctx.tenant, ctx.user, payload)


@router.post("/invitations/{invitation_id}/revoke")
def revoke_invitation(
    invitation_id: str,
    ctx: AccessContext = Depends(require_permission("invitation:write")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    InvitationService(db).revoke_invitation(ctx.tenant.id, UUID(invitation_id), ctx.user.id)
    return {"status": "revoked"}


@router.get("/onboarding", response_model=OnboardingStateResponse)
def get_onboarding(ctx: AccessContext = Depends(get_access_context), db: Session = Depends(get_db)):
    return TenantService(db).get_onboarding(ctx.tenant.id)


@router.patch("/onboarding", response_model=OnboardingStateResponse)
def patch_onboarding(
    payload: OnboardingStateUpdate,
    ctx: AccessContext = Depends(require_permission("onboarding:write")),
    db: Session = Depends(get_db),
):
    return TenantService(db).update_onboarding(ctx.tenant.id, payload)


@router.get("/subscription", response_model=SubscriptionSummary)
def get_subscription(ctx: AccessContext = Depends(get_access_context), db: Session = Depends(get_db)):
    return TenantService(db).get_subscription(ctx.tenant.id)


root_router = APIRouter(prefix="/api/v1/invitations", tags=["invitations"])


@root_router.post("/accept", response_model=InvitationAcceptResponse)
def accept_invitation(
    payload: InvitationAcceptRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    user = InvitationService(db).accept_invitation(payload, current_user=current_user)
    from app.models.entities import TenantInvitation

    invite = db.scalars(select(TenantInvitation).where(TenantInvitation.token == payload.token)).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return InvitationAcceptResponse(status="accepted", tenant_id=invite.tenant_id, user_id=user.id)
