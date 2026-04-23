from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    membership_id: UUID
    user_id: UUID
    full_name: str
    email: str
    role_code: str
    status: str


class TenantMemberPatch(BaseModel):
    """JSON may use ``status``; the Python attribute is ``membership_status`` for clarity."""

    model_config = ConfigDict(populate_by_name=True)

    role_code: str | None = None
    membership_status: str | None = Field(
        default=None,
        alias="status",
        description="Membership lifecycle: active or suspended",
    )
