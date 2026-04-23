from datetime import UTC, datetime
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models.entities import Role, Tenant, TenantInvitation, TenantMembership, User
from app.repositories.invitations import InvitationRepository
from app.schemas.invitation import InvitationAcceptRequest, InvitationCreateRequest, InvitationResponse
from app.services.audit import AuditService
from app.services.mail import (
    MailService,
    build_invite_accept_url,
    generate_invite_token,
    invitation_email_body,
    invitation_expiry,
)

settings = get_settings()
ALLOWED_TENANT_ROLES = {
    "tenant_admin",
    "director",
    "sales_user",
    "account_manager",
    "service_manager",
    "marketing_user",
}


class InvitationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvitationRepository(db)
        self.mail = MailService()
        self.audit = AuditService(db)

    def _to_response(self, invitation: TenantInvitation) -> InvitationResponse:
        expose_debug = settings.environment == "development" and settings.expose_invitation_token_in_response
        token = invitation.token if expose_debug else None
        accept_url = build_invite_accept_url(invitation.token if settings.environment == "development" else None)
        return InvitationResponse(
            id=invitation.id,
            email=invitation.email,
            role_to_assign=invitation.role_to_assign,
            status=invitation.status,
            accept_url=accept_url,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            created_at=invitation.created_at,
            debug_token=token,
        )

    def list_for_tenant(self, tenant_id: uuid.UUID):
        rows = self.repo.list_for_tenant(tenant_id)
        return [self._to_response(row) for row in rows]

    def create_invitation(self, tenant: Tenant, invited_by: User, payload: InvitationCreateRequest) -> InvitationResponse:
        role_code = payload.role_to_assign.strip().lower()
        if role_code not in ALLOWED_TENANT_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant role for invitation")

        role_exists = self.db.scalars(select(Role).where(Role.code == role_code)).first()
        if not role_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")

        email = payload.email.lower()
        existing_membership = self.db.scalars(
            select(TenantMembership)
            .join(User, User.id == TenantMembership.user_id)
            .where(TenantMembership.tenant_id == tenant.id, User.email == email, TenantMembership.status == "active")
        ).first()
        if existing_membership:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already an active member")

        duplicate_pending = self.repo.by_tenant_email_pending(tenant.id, email)
        if duplicate_pending:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pending invitation already exists")

        token = generate_invite_token()
        expires_at = invitation_expiry()

        invite = TenantInvitation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=email,
            role_to_assign=role_code,
            invited_by_user_id=invited_by.id,
            token=token,
            status="pending",
            expires_at=expires_at,
        )
        created = self.repo.create(invite)

        self.mail.send(
            to_email=created.email,
            subject=f"Invitation to join {tenant.name}",
            body=invitation_email_body(tenant.name, created.role_to_assign, created.token, created.expires_at),
        )

        self.audit.log(
            tenant_id=tenant.id,
            actor_user_id=invited_by.id,
            event_type="invitation.created",
            details={"invitation_id": str(created.id), "email": created.email, "role": created.role_to_assign},
        )
        self.db.commit()
        return self._to_response(created)

    def revoke_invitation(self, tenant_id: UUID, invitation_id: UUID, actor_user_id: UUID):
        invite = self.repo.get(invitation_id)
        if not invite or invite.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if invite.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending invites can be revoked")
        self.repo.revoke(invite)
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type="invitation.revoked",
            details={"invitation_id": str(invite.id), "email": invite.email},
        )
        self.db.commit()

    def accept_invitation(self, payload: InvitationAcceptRequest, current_user: User | None = None):
        invite = self.repo.by_token(payload.token)
        if not invite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

        if invite.status == "accepted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation already accepted")
        if invite.status == "revoked":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation was revoked")
        if invite.status == "expired":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")
        if invite.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation is not pending")

        invite_expiry = invite.expires_at
        if invite_expiry.tzinfo is None:
            invite_expiry = invite_expiry.replace(tzinfo=UTC)
        if invite_expiry < datetime.now(UTC):
            invite.status = "expired"
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")

        user = current_user
        if user:
            if user.email.lower() != invite.email.lower():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation email mismatch")
        else:
            existing = self.db.scalars(select(User).where(User.email == invite.email.lower())).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Account already exists for invite email. Please log in to accept.",
                )

            if not payload.full_name or not payload.password:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="full_name and password required")

            from app.core.security import get_password_hash

            user = User(
                id=uuid.uuid4(),
                email=invite.email.lower(),
                full_name=payload.full_name,
                password_hash=get_password_hash(payload.password),
                is_platform_admin=False,
            )
            self.db.add(user)
            self.db.flush()

        role = self.db.scalars(select(Role).where(Role.code == invite.role_to_assign)).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned role no longer exists")

        membership = self.db.scalars(
            select(TenantMembership).where(TenantMembership.tenant_id == invite.tenant_id, TenantMembership.user_id == user.id)
        ).first()
        membership_event = "membership.created"
        if membership:
            membership.role_id = role.id
            membership.status = "active"
            membership_event = "membership.updated"
        else:
            self.db.add(
                TenantMembership(
                    id=uuid.uuid4(),
                    tenant_id=invite.tenant_id,
                    user_id=user.id,
                    role_id=role.id,
                    status="active",
                )
            )

        invite.status = "accepted"
        invite.accepted_at = datetime.now(UTC)

        self.audit.log(
            tenant_id=invite.tenant_id,
            actor_user_id=user.id,
            event_type="invitation.accepted",
            details={"invitation_id": str(invite.id), "email": invite.email, "role": invite.role_to_assign},
        )
        self.audit.log(
            tenant_id=invite.tenant_id,
            actor_user_id=user.id,
            event_type=membership_event,
            details={"email": user.email, "role": invite.role_to_assign},
        )

        self.db.commit()
        return user
