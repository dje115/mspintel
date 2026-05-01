from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.ai_execution import AIExecutionOutcome, AIProductBlockState
from app.schemas.backup_health import BackupHealthWorkspaceResponse
from app.schemas.billing_integrity import BillingIntegrityWorkspaceResponse
from app.schemas.m365 import M365WorkspaceResponse
from app.schemas.workspace import (
    CommercialHubResponse,
    RecommendationListResponse,
    RecommendationPatch,
    RecommendationRow,
    RecommendationSyncResponse,
    RiskQueueResponse,
    RiskRecomputeResponse,
    ServiceRiskResponse,
)
from app.services.ai_execution_service import AIExecutionService
from app.services.ai_product_context import build_recommendation_explanation_variables
from app.services.ai_product_context import (
    build_backup_workspace_insights_variables,
    build_m365_workspace_opportunity_variables,
    build_m365_workspace_summary_variables,
)
from app.services.backup_health_service import BackupHealthService
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.m365_health_service import M365HealthService
from app.services.recommendation_signals_service import RecommendationSignalsService
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


@router.post("/recommendations/sync-from-signals", response_model=RecommendationSyncResponse)
def sync_recommendations_from_signals(
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    """Create, update, or complete open recommendations from live mapping, billing, tickets, quotes, and M365 signals."""
    stats = RecommendationSignalsService(db).sync(ctx.tenant.id)
    db.commit()
    return RecommendationSyncResponse(**stats)


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


@router.get("/m365-health", response_model=M365WorkspaceResponse)
def m365_health_workspace(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    raw = M365HealthService(db).build_workspace(ctx.tenant.id)
    return M365WorkspaceResponse(summary=raw["summary"], coverage_notes=raw["coverage_notes"], customers=raw["customers"])


@router.get("/m365-health/ai/latest", response_model=AIProductBlockState)
def get_m365_health_ai_latest(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "m365_hygiene_summary")


@router.post("/m365-health/ai/summary", response_model=AIExecutionOutcome)
def post_m365_health_ai_summary(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_m365_workspace_summary_variables(db, ctx.tenant.id)
    linked_count = int((variables.get("portfolio_context") or {}).get("portfolio_totals", {}).get("linked_count") or 0)
    if linked_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No linked Microsoft 365 posture rows are available yet. Run sync and complete mapping/import first.",
        )
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="m365_hygiene_summary",
        variables=variables,
        actor_user_id=ctx.user.id,
    )


@router.get("/m365-health/ai/opportunity/latest", response_model=AIProductBlockState)
def get_m365_health_ai_opportunity_latest(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "m365_upsell_opportunity")


@router.post("/m365-health/ai/opportunity", response_model=AIExecutionOutcome)
def post_m365_health_ai_opportunity(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_m365_workspace_opportunity_variables(db, ctx.tenant.id)
    linked_count = int((variables.get("portfolio_context") or {}).get("portfolio_totals", {}).get("linked_count") or 0)
    if linked_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No linked Microsoft 365 posture rows are available yet. Run sync and complete mapping/import first.",
        )
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="m365_upsell_opportunity",
        variables=variables,
        actor_user_id=ctx.user.id,
    )


@router.get("/backup-health", response_model=BackupHealthWorkspaceResponse)
def backup_health_workspace(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    raw = BackupHealthService(db).build_workspace(ctx.tenant.id)
    return BackupHealthWorkspaceResponse(
        summary=raw["summary"],
        coverage_notes=raw["coverage_notes"],
        connections=raw["connections"],
        customer_rollups=raw["customer_rollups"],
        fact_samples=raw["fact_samples"],
    )


@router.get("/backup-health/ai/latest", response_model=AIProductBlockState)
def get_backup_health_ai_latest(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "backup_coverage_insights")


@router.post("/backup-health/ai/insights", response_model=AIExecutionOutcome)
def post_backup_health_ai_insights(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_backup_workspace_insights_variables(db, ctx.tenant.id)
    fact_total = int((variables.get("portfolio_context") or {}).get("portfolio_totals", {}).get("total_protection_facts") or 0)
    if fact_total <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No backup protection facts are available yet. Configure a backup connector and run sync first.",
        )
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="backup_coverage_insights",
        variables=variables,
        actor_user_id=ctx.user.id,
    )


@router.get("/risk-queue", response_model=RiskQueueResponse)
def risk_queue(
    mode: str = Query(default="at_risk", description="at_risk | attention"),
    search: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    mapped_mode = "at_risk" if mode == "at_risk" else "attention"
    return WorkspaceService(db).risk_queue(
        ctx.tenant.id,
        mode=mapped_mode,
        search=search,
        owner_search=owner,
        page=page,
        page_size=page_size,
    )


@router.post("/risk-engine/recompute", response_model=RiskRecomputeResponse)
def recompute_risk_engine(
    customer_id: UUID | None = Query(default=None),
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    out = WorkspaceService(db).recompute_risk(ctx.tenant.id, customer_id=customer_id)
    db.commit()
    return out
