from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.tenant_profile import TenantAIContextResponse, TenantMspProfilePayload, TenantMspProfileResponse, TenantServiceCatalogResponse
from app.services.tenant_profile import TenantProfileService, build_tenant_ai_context

router = APIRouter(prefix="/api/tenant", tags=["tenant_profile"])


@router.get("/profile", response_model=TenantMspProfileResponse)
def get_profile(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return TenantProfileService(db).get_profile(ctx.tenant.id)


@router.put("/profile", response_model=TenantMspProfileResponse)
def put_profile(
    body: TenantMspProfilePayload,
    ctx: AccessContext = Depends(require_permission("onboarding:write")),
    db: Session = Depends(get_db),
):
    return TenantProfileService(db).put_profile(ctx.tenant.id, ctx.user.id, body)


@router.get("/service-catalogue", response_model=TenantServiceCatalogResponse)
def get_service_catalogue(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return TenantProfileService(db).get_service_catalog(ctx.tenant.id)


@router.put("/service-catalogue", response_model=TenantServiceCatalogResponse)
def put_service_catalogue(
    body: TenantServiceCatalogResponse,
    ctx: AccessContext = Depends(require_permission("onboarding:write")),
    db: Session = Depends(get_db),
):
    return TenantProfileService(db).put_service_catalog(ctx.tenant.id, ctx.user.id, body)


@router.get("/ai-context", response_model=TenantAIContextResponse)
def get_tenant_ai_context(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return build_tenant_ai_context(db, ctx.tenant.id)

