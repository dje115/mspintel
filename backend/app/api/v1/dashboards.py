from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.system import (
    ExecutiveDashboardResponse,
    SalesDashboardResponse,
    ServiceDashboardResponse,
)
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/api/v1/dashboards", tags=["dashboards"])


@router.get("/executive", response_model=ExecutiveDashboardResponse)
def executive(ctx: AccessContext = Depends(require_permission("dashboard:executive")), db: Session = Depends(get_db)):
    return DashboardService(db).executive(ctx.tenant.id)


@router.get("/sales", response_model=SalesDashboardResponse)
def sales(ctx: AccessContext = Depends(require_permission("dashboard:sales")), db: Session = Depends(get_db)):
    return DashboardService(db).sales(ctx.tenant.id)


@router.get("/service", response_model=ServiceDashboardResponse)
def service(ctx: AccessContext = Depends(require_permission("dashboard:service")), db: Session = Depends(get_db)):
    return DashboardService(db).service(ctx.tenant.id)
