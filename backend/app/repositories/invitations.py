from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.entities import TenantInvitation


class InvitationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_tenant(self, tenant_id: UUID):
        return self.db.scalars(
            select(TenantInvitation)
            .where(TenantInvitation.tenant_id == tenant_id)
            .order_by(TenantInvitation.created_at.desc())
        ).all()

    def create(self, invite: TenantInvitation) -> TenantInvitation:
        self.db.add(invite)
        self.db.commit()
        self.db.refresh(invite)
        return invite

    def by_token(self, token: str) -> TenantInvitation | None:
        return self.db.scalars(select(TenantInvitation).where(TenantInvitation.token == token)).first()

    def by_tenant_email_pending(self, tenant_id: UUID, email: str) -> TenantInvitation | None:
        return self.db.scalars(
            select(TenantInvitation).where(
                TenantInvitation.tenant_id == tenant_id,
                TenantInvitation.email == email.lower(),
                TenantInvitation.status == "pending",
            )
        ).first()

    def get(self, invitation_id: UUID) -> TenantInvitation | None:
        return self.db.get(TenantInvitation, invitation_id)

    def revoke(self, invitation: TenantInvitation) -> None:
        invitation.status = "revoked"
        invitation.updated_at = datetime.now(UTC)

    def expire_pending_past_expiry(self, now: datetime | None = None) -> int:
        """Mark ``pending`` invitations with ``expires_at`` in the past as ``expired`` (idempotent).

        Re-running updates zero rows. Uses UTC-aware ``now`` for comparisons so ORM/SQLite stay consistent.
        """
        ts = now or datetime.now(UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        stmt = (
            update(TenantInvitation)
            .where(
                TenantInvitation.status == "pending",
                TenantInvitation.expires_at < ts,
            )
            .values(status="expired", updated_at=ts)
            .execution_options(synchronize_session=False)
        )
        res = self.db.execute(stmt)
        self.db.commit()
        return int(res.rowcount or 0)
