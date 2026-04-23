"""Schemas for AI execution results and product-facing AI blocks."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AIExecutionOutcome(BaseModel):
    run_id: UUID
    status: str = Field(
        description="queued | running | succeeded | failed | unavailable | unsupported | skipped"
    )
    task_type: str
    text: str | None = None
    message: str | None = Field(default=None, description="Safe user-facing explanation when not succeeded")
    provider_family: str | None = None
    deployment_mode: str | None = None
    model_used: str | None = None
    prompt_definition_id: UUID | None = None
    prompt_version_id: UUID | None = None
    fallback_used: bool = False
    duration_ms: int | None = None
    completed_at: datetime | None = None


class AIProductBlockState(BaseModel):
    """Latest persisted generation for a UI surface (read model)."""

    status: str
    text: str | None = None
    message: str | None = None
    run_id: UUID | None = None
    last_completed_at: datetime | None = None
    provider_family: str | None = None
    model_used: str | None = None
    prompt_version_id: UUID | None = None


class AITaskRunRow(BaseModel):
    id: UUID
    tenant_id: UUID
    task_type: str
    status: str
    customer_id: UUID | None
    recommendation_id: UUID | None
    provider_family: str | None
    deployment_mode: str | None
    model_used: str | None
    prompt_definition_id: UUID | None
    prompt_version_id: UUID | None
    fallback_used: bool
    duration_ms: int | None
    error_summary: str | None
    output_summary: str | None
    created_at: datetime | None = None
    completed_at: datetime | None = None
