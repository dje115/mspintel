from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PlatformOverviewResponse(BaseModel):
    tenant_count: int
    user_count: int
    subscription_count: int
    app_version: str
    environment: str


class PlatformTenantRow(BaseModel):
    tenant_id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    onboarding_status: str | None = None
    onboarding_step: str | None = None
    subscription_status: str | None = None
    plan_code: str | None = None
    plan_name: str | None = None


class PlatformTenantListResponse(BaseModel):
    items: list[PlatformTenantRow]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int
