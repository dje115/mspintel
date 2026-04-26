from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.customers import CustomerRepository
from app.schemas.billing_integrity import FinanceCustomerPanel
from app.schemas.customer import CustomerDetailResponse, CustomerListItem, CustomerListResponse
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.workspace import WorkspaceService


class CustomerService:
    def __init__(self, db: Session):
        self.repo = CustomerRepository(db)
        self.workspace = WorkspaceService(db)

    def list_customers(self, tenant_id: UUID, search: str | None, status_filter: str | None, page: int, page_size: int):
        customers, total = self.repo.list_customers(tenant_id, search, status_filter, page, page_size)
        items: list[CustomerListItem] = []
        for customer in customers:
            score = self.repo.latest_score(tenant_id, customer.id)
            recs = self.repo.recommendation_summary(tenant_id, customer.id)
            items.append(
                CustomerListItem(
                    id=customer.id,
                    name=customer.name,
                    status=customer.status,
                    owner_name=customer.owner_name,
                    risk_score=score.risk_score if score else None,
                    attention_score=score.attention_score if score else None,
                    growth_score=score.growth_score if score else None,
                    next_best_action=recs[0] if recs else None,
                )
            )

        return CustomerListResponse(items=items, page=page, page_size=page_size, total=total)

    def get_customer_detail(self, tenant_id: UUID, customer_id: UUID) -> CustomerDetailResponse:
        customer = self.repo.get_customer(tenant_id, customer_id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

        score = self.repo.latest_score(tenant_id, customer_id)
        tickets, opps, quotes = self.repo.open_counts(tenant_id, customer_id)
        recs = self.repo.recommendation_summary(tenant_id, customer_id)
        actions = self.repo.recent_actions(tenant_id, customer_id)
        rec_rows, opp_rows, quote_rows = self.workspace.customer_workspace_slices(tenant_id, customer_id)

        fin_raw = BillingIntegrityService(self.repo.db).customer_finance_panel(tenant_id, customer_id)
        fin_raw.pop("error", None)
        finance_panel = FinanceCustomerPanel(**fin_raw)

        return CustomerDetailResponse(
            id=customer.id,
            name=customer.name,
            status=customer.status,
            owner_name=customer.owner_name,
            demo_profile=customer.demo_profile,
            finance=finance_panel,
            latest_scores={
                "risk_score": score.risk_score,
                "attention_score": score.attention_score,
                "growth_score": score.growth_score,
            }
            if score
            else None,
            open_tickets_count=tickets,
            open_opportunities_count=opps,
            open_quotes_count=quotes,
            recommendation_summary=recs,
            recent_actions=actions,
            recommendations=rec_rows,
            opportunities=opp_rows,
            quotes=quote_rows,
        )
