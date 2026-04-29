"""Review & QBR workspace: shaped context and persisted AI artefacts."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.models.entities import CustomerReviewAiArtifact
from app.repositories.customer_review_ai_artifacts import CustomerReviewAiArtifactRepository
from app.schemas.review_ai import (
    CustomerReviewArtifactListResponse,
    CustomerReviewArtifactOut,
    CustomerReviewLatestArtifactsResponse,
    ReviewAiGenerationResponse,
    ReviewWorkspaceContextResponse,
)
from app.services.customer import CustomerService
from app.services.review_ai_workspace import ARTIFACT_TASK_TYPES, ReviewAiWorkspaceService
from app.services.review_qbr_context import build_review_qbr_variables, context_hash_for_customer

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


def _artifact_out(row: CustomerReviewAiArtifact) -> CustomerReviewArtifactOut:
    ow = row.output_warnings
    if ow is not None and not isinstance(ow, list):
        ow = None
    return CustomerReviewArtifactOut(
        id=row.id,
        tenant_id=row.tenant_id,
        customer_id=row.customer_id,
        artifact_type=row.artifact_type,
        title=row.title,
        status=row.status,
        full_output_json=row.full_output_json if isinstance(row.full_output_json, dict) else None,
        full_output_text=row.full_output_text,
        short_context_json=row.short_context_json if isinstance(row.short_context_json, dict) else None,
        created_by_user_id=row.created_by_user_id,
        ai_task_run_id=row.ai_task_run_id,
        prompt_key=row.prompt_key,
        prompt_version_id=row.prompt_version_id,
        provider_family=row.provider_family,
        deployment_mode=row.deployment_mode,
        model_used=row.model_used,
        source_data_version=row.source_data_version,
        source_coverage_summary=row.source_coverage_summary if isinstance(row.source_coverage_summary, dict) else None,
        output_warnings=ow,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/{customer_id}/context", response_model=ReviewWorkspaceContextResponse)
def get_review_workspace_context(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    CustomerService(db).get_customer_detail(ctx.tenant.id, customer_id)
    variables = build_review_qbr_variables(
        db,
        ctx.tenant.id,
        customer_id,
        caller_name=ctx.user.full_name,
        caller_email=ctx.user.email,
        caller_role=ctx.role_code,
    )
    prev = variables.get("previous_ai_artifacts") or []
    return ReviewWorkspaceContextResponse(
        review_workspace=variables.get("review_workspace") or {},
        previous_ai_artifacts=prev if isinstance(prev, list) else [],
        source_data_version=context_hash_for_customer(db, ctx.tenant.id, customer_id),
    )


@router.get("/{customer_id}/ai/artifacts", response_model=CustomerReviewArtifactListResponse)
def list_review_artifacts(
    customer_id: UUID,
    artifact_type: str | None = Query(default=None),
    limit: int = Query(default=60, ge=1, le=200),
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    CustomerService(db).get_customer_detail(ctx.tenant.id, customer_id)
    repo = CustomerReviewAiArtifactRepository(db)
    rows = repo.list_for_customer(ctx.tenant.id, customer_id, artifact_type=artifact_type, limit=limit)
    return CustomerReviewArtifactListResponse(items=[_artifact_out(r) for r in rows])


@router.get("/{customer_id}/ai/artifacts/latest", response_model=CustomerReviewLatestArtifactsResponse)
def latest_review_artifacts(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    CustomerService(db).get_customer_detail(ctx.tenant.id, customer_id)
    repo = CustomerReviewAiArtifactRepository(db)
    by_type: dict[str, CustomerReviewArtifactOut | None] = {}
    for at in ARTIFACT_TASK_TYPES:
        row = repo.latest_for_type(ctx.tenant.id, customer_id, at)
        by_type[at] = _artifact_out(row) if row else None
    return CustomerReviewLatestArtifactsResponse(by_type=by_type)


@router.get("/{customer_id}/ai/artifacts/{artifact_id}", response_model=CustomerReviewArtifactOut)
def get_review_artifact(
    customer_id: UUID,
    artifact_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    CustomerService(db).get_customer_detail(ctx.tenant.id, customer_id)
    repo = CustomerReviewAiArtifactRepository(db)
    row = repo.get(ctx.tenant.id, artifact_id)
    if not row or row.customer_id != customer_id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return _artifact_out(row)


def _gen(
    db: Session,
    ctx: AccessContext,
    customer_id: UUID,
    artifact_type: str,
    *,
    email_tone: str | None = None,
) -> ReviewAiGenerationResponse:
    svc = ReviewAiWorkspaceService(db)
    return svc.generate_with_caller(
        tenant_id=ctx.tenant.id,
        customer_id=customer_id,
        actor_user_id=ctx.user.id,
        artifact_type=artifact_type,
        caller_name=ctx.user.full_name,
        caller_email=ctx.user.email,
        caller_role=ctx.role_code,
        email_tone=email_tone,
    )


@router.post("/{customer_id}/ai/agenda", response_model=ReviewAiGenerationResponse)
def post_review_agenda(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return _gen(db, ctx, customer_id, "review_agenda")


@router.post("/{customer_id}/ai/account-notes", response_model=ReviewAiGenerationResponse)
def post_review_account_notes(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return _gen(db, ctx, customer_id, "account_manager_notes")


@router.post("/{customer_id}/ai/call-script", response_model=ReviewAiGenerationResponse)
def post_review_call_script(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return _gen(db, ctx, customer_id, "call_script")


@router.post("/{customer_id}/ai/email-draft", response_model=ReviewAiGenerationResponse)
def post_review_email_draft(
    customer_id: UUID,
    tone: str | None = Query(default=None, description="professional | friendly | concise"),
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return _gen(db, ctx, customer_id, "customer_email_draft", email_tone=tone)


@router.post("/{customer_id}/ai/customer-report", response_model=ReviewAiGenerationResponse)
def post_review_customer_report(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return _gen(db, ctx, customer_id, "customer_report")
