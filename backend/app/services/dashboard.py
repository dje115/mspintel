from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.dashboards import DashboardRepository
from app.schemas.system import ExecutiveDashboardResponse, SalesDashboardResponse, ServiceDashboardResponse
from app.services.risk_engine_v1 import RiskEngineV1Service


class DashboardService:
    def __init__(self, db: Session):
        self.repo = DashboardRepository(db)

    def executive(self, tenant_id: UUID) -> ExecutiveDashboardResponse:
        RiskEngineV1Service(self.repo.db).ensure_scores(tenant_id)
        return ExecutiveDashboardResponse(
            customers=self.repo.customer_count(tenant_id),
            high_risk_customers=self.repo.high_risk_count(tenant_id),
            open_recommendations=self.repo.open_recommendations(tenant_id),
            lost_quotes_revisit_count=self.repo.lost_quotes(tenant_id),
        )

    def sales(self, tenant_id: UUID) -> SalesDashboardResponse:
        return SalesDashboardResponse(
            customers=self.repo.customer_count(tenant_id),
            open_sales_recommendations=self.repo.open_recommendations(tenant_id, scope="sales"),
            quote_reactivation_count=self.repo.lost_quotes(tenant_id),
        )

    def service(self, tenant_id: UUID) -> ServiceDashboardResponse:
        open_tickets = self.repo.open_tickets(tenant_id)
        return ServiceDashboardResponse(
            open_tickets=open_tickets,
            weak_ticket_quality_count=max(0, open_tickets // 3),
            high_support_burden_customers=max(0, open_tickets // 2),
        )
