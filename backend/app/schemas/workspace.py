"""Tenant workspace operational views (recommendations, commercial hub, service risk)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RecommendationRow(BaseModel):
    id: UUID
    customer_id: UUID | None
    customer_name: str | None
    owner_name: str | None
    scope: str
    status: str
    summary: str
    category: str = Field(description="Alias for scope / queue type")
    priority: str = Field(description="Derived: high | medium | standard")
    suggested_next_action: str
    created_at: datetime | None = None


class RecommendationListResponse(BaseModel):
    items: list[RecommendationRow]
    page: int
    page_size: int
    total: int


class RecommendationPatch(BaseModel):
    status: Literal["open", "accepted", "rejected", "completed"]


class OpportunityRow(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str | None
    title: str
    status: str
    value_cents: int | None = None
    revisit_reason: str | None = None
    suggested_next_action: str
    created_at: datetime | None = None


class QuoteRow(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str | None
    title: str
    status: str
    value_cents: int | None = None
    revisit_reason: str | None = None
    suggested_next_action: str
    created_at: datetime | None = None


class CommercialHubResponse(BaseModel):
    opportunities: list[OpportunityRow]
    lost_quotes: list[QuoteRow]
    open_quotes: list[QuoteRow]


class ServiceRiskSection(BaseModel):
    title: str
    summary: str
    metrics: dict[str, int | str]
    placeholder: bool = False


class ServiceRiskResponse(BaseModel):
    backup: ServiceRiskSection
    service_delivery: ServiceRiskSection
