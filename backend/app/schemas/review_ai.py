"""API models for Review/QBR AI workspace."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ai_execution import AIExecutionOutcome


class ReviewAiGenerationResponse(AIExecutionOutcome):
    """AI run outcome plus persisted artefact metadata for the Reviews workspace."""

    artifact_id: UUID | None = None
    structured_output: dict[str, Any] | None = None
    short_context: dict[str, Any] | None = None
    output_warnings: list[str] = Field(default_factory=list)


class CustomerReviewArtifactOut(BaseModel):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    artifact_type: str
    title: str | None
    status: str
    full_output_json: dict[str, Any] | None = None
    full_output_text: str | None = None
    short_context_json: dict[str, Any] | None = None
    created_by_user_id: UUID | None = None
    ai_task_run_id: UUID | None = None
    prompt_key: str | None = None
    prompt_version_id: UUID | None = None
    provider_family: str | None = None
    deployment_mode: str | None = None
    model_used: str | None = None
    source_data_version: str | None = None
    source_coverage_summary: dict[str, Any] | None = None
    output_warnings: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomerReviewArtifactListResponse(BaseModel):
    items: list[CustomerReviewArtifactOut]


class CustomerReviewLatestArtifactsResponse(BaseModel):
    """Latest succeeded artefact per requested type (null if none)."""

    by_type: dict[str, CustomerReviewArtifactOut | None]


class ReviewWorkspaceContextResponse(BaseModel):
    """Read-only shaped context for the Review prep UI (connector-backed, single customer)."""

    review_workspace: dict[str, Any]
    previous_ai_artifacts: list[dict[str, Any]]
    source_data_version: str | None = None
