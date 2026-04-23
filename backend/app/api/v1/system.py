from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.system import SystemStatusResponse
from app.services.system import SystemService

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def system_status(
    _: AccessContext = Depends(require_permission("system:read")),
    db: Session = Depends(get_db),
):
    return SystemService(db).status()
