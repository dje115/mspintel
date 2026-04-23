from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Customer, Opportunity, Quote, Recommendation
from app.repositories.tenant_scope import tenant_scoped


def _priority_for_scope(scope: str) -> str:
    if scope == "executive":
        return "high"
    if scope in ("sales", "service"):
        return "medium"
    return "standard"


def _next_action_for_rec(scope: str, summary: str) -> str:
    if scope == "sales":
        return "Schedule commercial follow-up"
    if scope == "service":
        return "Review service delivery plan"
    return "Review with account owner"


class WorkspaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def _apply_recommendation_filters(
        self, stmt, tenant_id: UUID, status: str | None, scope: str | None, customer_id: UUID | None, owner_search: str | None
    ):
        stmt = stmt.where(Recommendation.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Recommendation.status == status)
        if scope:
            stmt = stmt.where(Recommendation.scope == scope)
        if customer_id:
            stmt = stmt.where(Recommendation.customer_id == customer_id)
        if owner_search:
            stmt = stmt.where(Customer.owner_name.ilike(f"%{owner_search}%"))
        return stmt

    def list_recommendations(
        self,
        tenant_id: UUID,
        *,
        status: str | None,
        scope: str | None,
        customer_id: UUID | None,
        owner_search: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Recommendation, str | None, str | None]], int]:
        count_stmt = self._apply_recommendation_filters(
            select(func.count(Recommendation.id)).select_from(Recommendation).outerjoin(
                Customer, Recommendation.customer_id == Customer.id
            ),
            tenant_id,
            status,
            scope,
            customer_id,
            owner_search,
        )
        total = int(self.db.scalar(count_stmt) or 0)
        list_stmt = self._apply_recommendation_filters(
            select(Recommendation, Customer.name, Customer.owner_name)
            .select_from(Recommendation)
            .outerjoin(Customer, Recommendation.customer_id == Customer.id),
            tenant_id,
            status,
            scope,
            customer_id,
            owner_search,
        )
        rows = self.db.execute(
            list_stmt.order_by(Recommendation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return [(r, name, owner) for r, name, owner in rows], total

    def get_recommendation(self, tenant_id: UUID, rec_id: UUID) -> Recommendation | None:
        stmt = tenant_scoped(select(Recommendation), Recommendation, tenant_id).where(Recommendation.id == rec_id)
        return self.db.scalars(stmt).first()

    def list_opportunities(self, tenant_id: UUID) -> list[tuple[Opportunity, str | None]]:
        stmt = (
            select(Opportunity, Customer.name)
            .where(Opportunity.tenant_id == tenant_id)
            .join(Customer, Opportunity.customer_id == Customer.id)
            .order_by(Opportunity.created_at.desc())
        )
        return list(self.db.execute(stmt).all())

    def list_quotes(self, tenant_id: UUID, statuses: list[str] | None = None) -> list[tuple[Quote, str | None]]:
        stmt = (
            select(Quote, Customer.name)
            .where(Quote.tenant_id == tenant_id)
            .join(Customer, Quote.customer_id == Customer.id)
        )
        if statuses:
            stmt = stmt.where(Quote.status.in_(statuses))
        stmt = stmt.order_by(Quote.created_at.desc())
        return list(self.db.execute(stmt).all())

    def open_ticket_count(self, tenant_id: UUID) -> int:
        from app.models.entities import Ticket

        stmt = tenant_scoped(select(Ticket), Ticket, tenant_id).where(Ticket.status == "open")
        return int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)

    def at_risk_customer_count(self, tenant_id: UUID) -> int:
        stmt = tenant_scoped(select(Customer), Customer, tenant_id).where(Customer.status == "at_risk")
        return int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)

    def lost_quote_count(self, tenant_id: UUID) -> int:
        stmt = tenant_scoped(select(Quote), Quote, tenant_id).where(Quote.status == "lost")
        return int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)

    def list_opportunities_for_customer(self, tenant_id: UUID, customer_id: UUID) -> list[tuple[Opportunity, str | None]]:
        stmt = (
            select(Opportunity, Customer.name)
            .where(Opportunity.tenant_id == tenant_id, Opportunity.customer_id == customer_id)
            .outerjoin(Customer, Opportunity.customer_id == Customer.id)
            .order_by(Opportunity.created_at.desc())
        )
        return list(self.db.execute(stmt).all())

    def list_quotes_for_customer(self, tenant_id: UUID, customer_id: UUID) -> list[tuple[Quote, str | None]]:
        stmt = (
            select(Quote, Customer.name)
            .where(Quote.tenant_id == tenant_id, Quote.customer_id == customer_id)
            .outerjoin(Customer, Quote.customer_id == Customer.id)
            .order_by(Quote.created_at.desc())
        )
        return list(self.db.execute(stmt).all())
