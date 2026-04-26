from uuid import UUID

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.billing_integrity import FinanceCustomerPanel
from app.schemas.workspace import OpportunityRow, QuoteRow, RecommendationRow


class CustomerListItem(BaseModel):
    id: UUID
    name: str
    status: str
    owner_name: str | None
    risk_score: int | None
    attention_score: int | None
    growth_score: int | None
    next_best_action: str | None


class CustomerListResponse(BaseModel):
    items: list[CustomerListItem]
    page: int
    page_size: int
    total: int


class CustomerDetailResponse(BaseModel):
    id: UUID
    name: str
    status: str
    owner_name: str | None
    demo_profile: dict[str, Any] | None = None
    finance: FinanceCustomerPanel | None = None
    latest_scores: dict[str, int] | None
    open_tickets_count: int
    open_opportunities_count: int
    open_quotes_count: int
    recommendation_summary: list[str]
    recent_actions: list[str]
    recommendations: list[RecommendationRow] = Field(default_factory=list)
    opportunities: list[OpportunityRow] = Field(default_factory=list)
    quotes: list[QuoteRow] = Field(default_factory=list)
