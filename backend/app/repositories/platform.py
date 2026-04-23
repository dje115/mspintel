from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import OnboardingState, Plan, Subscription, Tenant


class PlatformRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_subscriptions(self) -> int:
        return self.db.query(Subscription).count()

    def list_tenants_page(self, *, page: int, page_size: int) -> tuple[list[tuple[Tenant, Subscription | None, Plan | None, OnboardingState | None]], int]:
        total = self.db.query(Tenant).count()
        offset = (page - 1) * page_size
        stmt = (
            select(Tenant, Subscription, Plan, OnboardingState)
            .outerjoin(Subscription, Subscription.tenant_id == Tenant.id)
            .outerjoin(Plan, Plan.id == Subscription.plan_id)
            .outerjoin(OnboardingState, OnboardingState.tenant_id == Tenant.id)
            .order_by(Tenant.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = list(self.db.execute(stmt).all())
        return rows, total
