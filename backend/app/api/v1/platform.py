from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.access import BearerIdentity, get_platform_admin
from app.api.deps.db import get_db
from app.schemas.platform import PlatformOverviewResponse, PlatformTenantListResponse
from app.schemas.system import SystemStatusResponse
from app.services.platform import PlatformService

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


@router.get("/overview", response_model=PlatformOverviewResponse)
def platform_overview(
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> PlatformOverviewResponse:
    return PlatformService(db).overview()


@router.get("/tenants", response_model=PlatformTenantListResponse)
def platform_tenants(
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PlatformTenantListResponse:
    return PlatformService(db).tenants(page=page, page_size=page_size)


@router.get("/system-status", response_model=SystemStatusResponse)
def platform_system_status(
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> SystemStatusResponse:
    return PlatformService(db).system_status()
