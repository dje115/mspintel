from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Role, TenantMembership, User


class MembershipRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_with_user_role(self, tenant_id: UUID, membership_id: UUID) -> tuple[TenantMembership, User, Role] | None:
        row = self.db.execute(
            select(TenantMembership, User, Role)
            .join(User, TenantMembership.user_id == User.id)
            .join(Role, TenantMembership.role_id == Role.id)
            .where(TenantMembership.id == membership_id, TenantMembership.tenant_id == tenant_id)
        ).first()
        if not row:
            return None
        return row[0], row[1], row[2]

    def count_active_tenant_admins(self, tenant_id: UUID) -> int:
        admin_role_id = self.db.scalars(select(Role.id).where(Role.code == "tenant_admin")).first()
        if not admin_role_id:
            return 0
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(TenantMembership)
                .where(
                    TenantMembership.tenant_id == tenant_id,
                    TenantMembership.role_id == admin_role_id,
                    TenantMembership.status == "active",
                )
            )
            or 0
        )

    def role_id_for_code(self, code: str) -> UUID | None:
        rid = self.db.scalars(select(Role.id).where(Role.code == code)).first()
        return rid
