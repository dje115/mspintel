from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import OnboardingState, Plan, Subscription, TenantMembership


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def memberships(self, tenant_id: UUID):
        return self.db.execute(
            select(TenantMembership).where(TenantMembership.tenant_id == tenant_id)
        ).scalars().all()

    def onboarding(self, tenant_id: UUID) -> OnboardingState | None:
        return self.db.scalars(select(OnboardingState).where(OnboardingState.tenant_id == tenant_id)).first()

    def subscription(self, tenant_id: UUID) -> tuple[Subscription, Plan] | None:
        row = self.db.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.tenant_id == tenant_id)
        ).first()
        return row if row else None
