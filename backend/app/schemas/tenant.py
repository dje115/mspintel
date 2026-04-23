from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OnboardingStateResponse(BaseModel):
    tenant_id: UUID
    status: str
    step: str


class OnboardingStateUpdate(BaseModel):
    status: str | None = None
    step: str | None = None


class SubscriptionSummary(BaseModel):
    tenant_id: UUID
    plan_code: str
    plan_name: str
    status: str


class TenantMembershipResponse(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    role_code: str
    status: str


class CurrentTenantResponse(BaseModel):
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    role_code: str


class TenantMemberResponse(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    role_code: str
    status: str
