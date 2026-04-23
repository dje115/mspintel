from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext
from app.domain.membership_rules import (
    ASSIGNABLE_TENANT_ROLE_CODES,
    MEMBERSHIP_STATUSES,
    ROLES_THAT_MAY_ASSIGN_TENANT_ADMIN,
)
from app.models.entities import Role, TenantMembership, User
from app.repositories.memberships import MembershipRepository
from app.schemas.tenant import TenantMemberResponse
from app.services.audit import AuditService


class MembershipService:
    """Tenant-scoped membership updates; see ``app.domain.membership_rules``."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = MembershipRepository(db)
        self.audit = AuditService(db)

    def _normalize_role_code(self, raw: str | None) -> str | None:
        if raw is None:
            return None
        s = raw.strip().lower()
        return s or None

    def _assert_assign_tenant_admin_allowed(self, actor: AccessContext, new_role_code: str) -> None:
        if new_role_code != "tenant_admin":
            return
        if actor.is_platform_admin:
            return
        if actor.role_code in ROLES_THAT_MAY_ASSIGN_TENANT_ADMIN:
            return
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only tenant admins or platform operators may assign the tenant_admin role",
        )

    def _last_active_admin_guard(
        self,
        tenant_id: UUID,
        target: TenantMembership,
        old_role_code: str,
        new_role_code: str,
        new_status: str,
    ) -> None:
        was_active_admin = target.status == "active" and old_role_code == "tenant_admin"
        will_active_admin = new_status == "active" and new_role_code == "tenant_admin"
        if was_active_admin and not will_active_admin:
            admins = self.repo.count_active_tenant_admins(tenant_id)
            if admins < 2:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove or demote the last active tenant admin for this workspace",
                )

    def _response_for_membership(self, membership: TenantMembership) -> TenantMemberResponse:
        user = self.db.get(User, membership.user_id)
        role_row = self.db.get(Role, membership.role_id)
        if not user or not role_row:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Membership reload failed"
            )
        return TenantMemberResponse(
            membership_id=membership.id,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            role_code=role_row.code,
            status=membership.status,
        )

    def update_membership(
        self,
        actor: AccessContext,
        membership_id: UUID,
        *,
        role_code: str | None,
        membership_status: str | None,
    ) -> TenantMemberResponse:
        row = self.repo.get_with_user_role(actor.tenant.id, membership_id)
        if not row:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Membership not found")

        membership, _user, role = row
        old_role_code = role.code
        old_status = membership.status

        if role_code is None and membership_status is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="At least one of role_code or status is required",
            )

        if role_code is not None:
            normalized_role = self._normalize_role_code(role_code)
            if not normalized_role:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tenant role",
                )
            new_role_code = normalized_role
        else:
            new_role_code = old_role_code

        if membership_status is None:
            new_status = old_status
        else:
            st = membership_status.strip().lower()
            if not st:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid membership status",
                )
            new_status = st

        if new_role_code not in ASSIGNABLE_TENANT_ROLE_CODES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid tenant role"
            )

        if new_status not in MEMBERSHIP_STATUSES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid membership status"
            )

        if new_role_code == old_role_code and new_status == old_status:
            return self._response_for_membership(membership)

        self._assert_assign_tenant_admin_allowed(actor, new_role_code)
        self._last_active_admin_guard(actor.tenant.id, membership, old_role_code, new_role_code, new_status)

        new_role_id = self.repo.role_id_for_code(new_role_code)
        if not new_role_id:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Role not found")

        membership.role_id = new_role_id
        membership.status = new_status

        self.audit.log(
            tenant_id=actor.tenant.id,
            actor_user_id=actor.user.id,
            event_type="membership.updated",
            details={
                "membership_id": str(membership.id),
                "target_user_id": str(membership.user_id),
                "old_role_code": old_role_code,
                "new_role_code": new_role_code,
                "old_status": old_status,
                "new_status": new_status,
            },
        )
        self.db.commit()
        self.db.refresh(membership)
        return self._response_for_membership(membership)
