from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.ai_foundation import (
    AIProviderCreateBody,
    AIProviderSafe,
    ResolvedAITaskResponse,
    TenantAiSettingsPatch,
    TenantAiSettingsResponse,
    TenantAiTaskRoutesPatch,
    TenantAiTaskRouteRow,
)
from app.services.ai_runtime_resolver import AIRuntimeResolver
from app.services.tenant_ai_application import TenantAiApplicationService, provider_to_safe

router = APIRouter(prefix="/api/v1/ai", tags=["tenant-ai"])


@router.get("/settings", response_model=TenantAiSettingsResponse)
def get_ai_settings(
    ctx: AccessContext = Depends(require_permission("ai:view")),
    db: Session = Depends(get_db),
):
    return TenantAiApplicationService(db).get_settings(ctx.tenant.id)


@router.patch("/settings", response_model=TenantAiSettingsResponse)
def patch_ai_settings(
    body: TenantAiSettingsPatch,
    ctx: AccessContext = Depends(require_permission("ai:configure")),
    db: Session = Depends(get_db),
):
    return TenantAiApplicationService(db).patch_settings(ctx.tenant.id, ctx.user.id, body)


@router.get("/task-routes", response_model=list[TenantAiTaskRouteRow])
def list_task_routes(
    ctx: AccessContext = Depends(require_permission("ai:view")),
    db: Session = Depends(get_db),
):
    return TenantAiApplicationService(db).list_routes(ctx.tenant.id)


@router.patch("/task-routes", response_model=list[TenantAiTaskRouteRow])
def patch_task_routes(
    body: TenantAiTaskRoutesPatch,
    ctx: AccessContext = Depends(require_permission("ai:configure")),
    db: Session = Depends(get_db),
):
    return TenantAiApplicationService(db).patch_routes(ctx.tenant.id, ctx.user.id, body)


@router.get("/providers", response_model=list[AIProviderSafe])
def list_tenant_providers(
    ctx: AccessContext = Depends(require_permission("ai:view")),
    db: Session = Depends(get_db),
):
    from app.repositories.tenant_ai_config import TenantAiConfigRepository

    svc = TenantAiConfigRepository(db)
    return [provider_to_safe(p) for p in svc.list_ai_providers(ctx.tenant.id)]


@router.post("/providers", response_model=AIProviderSafe)
def create_tenant_provider(
    body: AIProviderCreateBody,
    ctx: AccessContext = Depends(require_permission("ai:configure")),
    db: Session = Depends(get_db),
):
    name = body.display_label or body.provider_family
    return TenantAiApplicationService(db).create_tenant_provider(
        ctx.tenant.id,
        ctx.user.id,
        catalog_code=body.catalog_code,
        provider_family=body.provider_family,
        deployment_mode=body.deployment_mode,
        display_label=body.display_label,
        base_url=body.base_url,
        settings=body.settings,
        provider_name=name[:60],
    )


@router.get("/resolve/{task_type}", response_model=ResolvedAITaskResponse)
def resolve_task(
    task_type: str,
    ctx: AccessContext = Depends(require_permission("ai:view")),
    db: Session = Depends(get_db),
):
    r = AIRuntimeResolver(db).resolve(ctx.tenant.id, task_type, include_prompt_text=True)
    return ResolvedAITaskResponse(
        tenant_id=r.tenant_id,
        task_type=r.task_type,
        enabled=r.enabled,
        provider_family=r.provider_family,
        deployment_mode=r.deployment_mode,
        model=r.model,
        ai_provider_id=r.ai_provider_id,
        prompt_key=r.prompt_key,
        prompt_definition_id=r.prompt_definition_id,
        prompt_version_id=r.prompt_version_id,
        prompt_text=r.prompt_text,
        fallback_ai_provider_id=r.fallback_ai_provider_id,
        fallback_provider_family=r.fallback_provider_family,
        fallback_deployment_mode=r.fallback_deployment_mode,
        fallback_model=r.fallback_model,
    )
