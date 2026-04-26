from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.ai_execution import AIExecutionOutcome, AIProductBlockState
from app.schemas.billing_integrity import BillingIntegrityWorkspaceResponse
from app.schemas.workspace import (
    CommercialHubResponse,
    RecommendationListResponse,
    RecommendationPatch,
    RecommendationRow,
    ServiceRiskResponse,
)
from app.services.ai_execution_service import AIExecutionService
from app.services.ai_product_context import build_recommendation_explanation_variables
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.workspace import WorkspaceService

router = APIRouter(prefix="/api/v1/workspace", tags=["workspace"])


@router.get("/recommendations", response_model=RecommendationListResponse)
def list_recommendations(
    status: str | None = Query(default=None, description="open | accepted | rejected | completed"),
    scope: str | None = Query(default=None, description="executive | sales | service"),
    customer_id: UUID | None = Query(default=None),
    owner: str | None = Query(default=None, description="Filter by account owner name (contains)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    """Operational queue of recommendations with account context."""
    return WorkspaceService(db).list_recommendations(
        ctx.tenant.id,
        status=status,
        scope=scope,
        customer_id=customer_id,
        owner_search=owner,
        page=page,
        page_size=page_size,
    )


@router.get("/recommendations/{recommendation_id}/ai/explanation", response_model=AIProductBlockState)
def get_recommendation_explanation_state(
    recommendation_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(
        ctx.tenant.id, "recommendation_explanation", recommendation_id=recommendation_id
    )


@router.post("/recommendations/{recommendation_id}/ai/explanation", response_model=AIExecutionOutcome)
def post_recommendation_explanation(
    recommendation_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_recommendation_explanation_variables(db, ctx.tenant.id, recommendation_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="recommendation_explanation",
        variables=variables,
        actor_user_id=ctx.user.id,
        recommendation_id=recommendation_id,
    )


@router.patch("/recommendations/{recommendation_id}", response_model=RecommendationRow)
def patch_recommendation(
    recommendation_id: UUID,
    body: RecommendationPatch,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    """Accept, reject, or complete a recommendation (tenant admins)."""
    return WorkspaceService(db).patch_recommendation(ctx.tenant.id, recommendation_id, body.status)


@router.get("/commercial", response_model=CommercialHubResponse)
def commercial_hub(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    """Opportunities and quotes for commercial follow-up (lost quotes, open pipeline)."""
    return WorkspaceService(db).commercial_hub(ctx.tenant.id)


@router.get("/service-risk", response_model=ServiceRiskResponse)
def service_risk(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    """Backup and service-delivery risk overview (placeholder + live counts where available)."""
    return WorkspaceService(db).service_risk(ctx.tenant.id)


@router.get("/billing-integrity", response_model=BillingIntegrityWorkspaceResponse)
def billing_integrity_workspace(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    """Revenue assurance workspace: canonical finance coverage and mismatch heuristics."""
    raw = BillingIntegrityService(db).build_workspace(ctx.tenant.id)
    return BillingIntegrityWorkspaceResponse(
        summary=raw["summary"],
        coverage_notes=raw["coverage_notes"],
        accounts=raw["accounts"],
    )
