import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.access import BearerIdentity, get_platform_admin
from app.api.deps.db import get_db
from app.models.entities import AIProviderCatalog, AITaskRun
from app.schemas.ai_execution import AITaskRunRow
from app.schemas.ai_foundation import AIProviderCatalogCreate, AIProviderCatalogRow
from app.services.audit import AuditService

router = APIRouter(prefix="/api/v1/platform/ai", tags=["platform-ai"])


@router.get("/task-runs", response_model=list[AITaskRunRow])
def list_ai_task_runs(
    limit: int = Query(default=80, ge=1, le=200),
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(AITaskRun).order_by(AITaskRun.created_at.desc()).limit(limit)).all()
    return [
        AITaskRunRow(
            id=r.id,
            tenant_id=r.tenant_id,
            task_type=r.task_type,
            status=r.status,
            customer_id=r.customer_id,
            recommendation_id=r.recommendation_id,
            provider_family=r.provider_family,
            deployment_mode=r.deployment_mode,
            model_used=r.model_used,
            prompt_definition_id=r.prompt_definition_id,
            prompt_version_id=r.prompt_version_id,
            fallback_used=bool(r.fallback_used),
            duration_ms=r.duration_ms,
            error_summary=r.error_summary,
            output_summary=r.output_summary,
            created_at=r.created_at,
            completed_at=r.completed_at,
        )
        for r in rows
    ]


@router.get("/providers/catalog", response_model=list[AIProviderCatalogRow])
def list_provider_catalog(
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(AIProviderCatalog).order_by(AIProviderCatalog.sort_order, AIProviderCatalog.code)).all()
    return [
        AIProviderCatalogRow(
            id=r.id,
            code=r.code,
            provider_family=r.provider_family,
            deployment_mode=r.deployment_mode,
            display_name=r.display_name,
            description=r.description,
            sort_order=r.sort_order,
        )
        for r in rows
    ]


@router.post("/providers/catalog", response_model=AIProviderCatalogRow)
def create_catalog_entry(
    body: AIProviderCatalogCreate,
    ctx: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    dup = db.scalars(select(AIProviderCatalog).where(AIProviderCatalog.code == body.code)).first()
    if dup:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="code already exists")
    row = AIProviderCatalog(
        id=uuid.uuid4(),
        code=body.code,
        provider_family=body.provider_family,
        deployment_mode=body.deployment_mode,
        display_name=body.display_name,
        description=body.description,
        sort_order=body.sort_order,
    )
    db.add(row)
    AuditService(db).log(
        tenant_id=None,
        actor_user_id=ctx.user.id,
        event_type="ai.platform.catalog.created",
        details={"code": body.code, "provider_family": body.provider_family, "deployment_mode": body.deployment_mode},
    )
    db.commit()
    db.refresh(row)
    return AIProviderCatalogRow(
        id=row.id,
        code=row.code,
        provider_family=row.provider_family,
        deployment_mode=row.deployment_mode,
        display_name=row.display_name,
        description=row.description,
        sort_order=row.sort_order,
    )
