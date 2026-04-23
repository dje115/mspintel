from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Customer, Quote, Recommendation, Ticket
from app.repositories.tenant_scope import tenant_scoped


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def customer_count(self, tenant_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(tenant_scoped(select(Customer), Customer, tenant_id).subquery())
            )
            or 0
        )

    def high_risk_count(self, tenant_id: UUID) -> int:
        # Placeholder risk heuristic for scaffold phase.
        return min(self.customer_count(tenant_id), 2)

    def open_recommendations(self, tenant_id: UUID, scope: str | None = None) -> int:
        stmt = tenant_scoped(select(Recommendation), Recommendation, tenant_id).where(
            Recommendation.status == "open"
        )
        if scope:
            stmt = stmt.where(Recommendation.scope == scope)
        return int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)

    def open_tickets(self, tenant_id: UUID) -> int:
        stmt = tenant_scoped(select(Ticket), Ticket, tenant_id).where(Ticket.status == "open")
        return int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)

    def lost_quotes(self, tenant_id: UUID) -> int:
        stmt = tenant_scoped(select(Quote), Quote, tenant_id).where(Quote.status == "lost")
        return int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
