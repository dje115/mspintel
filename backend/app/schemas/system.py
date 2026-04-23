from pydantic import BaseModel


class ExecutiveDashboardResponse(BaseModel):
    customers: int
    high_risk_customers: int
    open_recommendations: int
    lost_quotes_revisit_count: int


class SalesDashboardResponse(BaseModel):
    customers: int
    open_sales_recommendations: int
    quote_reactivation_count: int


class ServiceDashboardResponse(BaseModel):
    open_tickets: int
    weak_ticket_quality_count: int
    high_support_burden_customers: int


class SystemStatusResponse(BaseModel):
    api: str
    environment: str
    version: str
    db: str
    redis: str
    tenant_count: int
    user_count: int
    source_connection_count: int
