from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Action, AccountScore, Customer, Opportunity, Quote, Recommendation, Ticket
from app.repositories.tenant_scope import tenant_scoped


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_customers(self, tenant_id: UUID, search: str | None, status: str | None, page: int, page_size: int):
        stmt = tenant_scoped(select(Customer), Customer, tenant_id)
        if search:
            stmt = stmt.where(Customer.name.ilike(f"%{search}%"))
        if status:
            stmt = stmt.where(Customer.status == status)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.db.scalars(
            stmt.order_by(Customer.name).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return rows, total

    def get_customer(self, tenant_id: UUID, customer_id: UUID):
        stmt = tenant_scoped(select(Customer), Customer, tenant_id).where(Customer.id == customer_id)
        return self.db.scalars(stmt).first()

    def latest_score(self, tenant_id: UUID, customer_id: UUID):
        stmt = tenant_scoped(select(AccountScore), AccountScore, tenant_id).where(
            AccountScore.customer_id == customer_id
        )
        return self.db.scalars(stmt.order_by(AccountScore.created_at.desc()).limit(1)).first()

    def open_counts(self, tenant_id: UUID, customer_id: UUID):
        tickets = self.db.scalar(
            select(func.count()).select_from(
                tenant_scoped(select(Ticket), Ticket, tenant_id)
                .where(Ticket.customer_id == customer_id, Ticket.status == "open")
                .subquery()
            )
        )
        opps = self.db.scalar(
            select(func.count()).select_from(
                tenant_scoped(select(Opportunity), Opportunity, tenant_id)
                .where(Opportunity.customer_id == customer_id, Opportunity.status == "open")
                .subquery()
            )
        )
        quotes = self.db.scalar(
            select(func.count()).select_from(
                tenant_scoped(select(Quote), Quote, tenant_id)
                .where(Quote.customer_id == customer_id, Quote.status.in_(["open", "lost"]))
                .subquery()
            )
        )
        return int(tickets or 0), int(opps or 0), int(quotes or 0)

    def recommendation_summary(self, tenant_id: UUID, customer_id: UUID) -> list[str]:
        stmt = tenant_scoped(select(Recommendation.summary), Recommendation, tenant_id).where(
            Recommendation.customer_id == customer_id
        )
        return list(self.db.scalars(stmt.limit(5)).all())

    def recent_actions(self, tenant_id: UUID, customer_id: UUID) -> list[str]:
        stmt = tenant_scoped(select(Action.description), Action, tenant_id).where(
            Action.customer_id == customer_id
        )
        return list(self.db.scalars(stmt.order_by(Action.created_at.desc()).limit(5)).all())
