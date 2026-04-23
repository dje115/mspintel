from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.models.entities import SourceSystemConnection
from app.schemas.integrations import SourceConnectionResponse

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.get("/connections", response_model=list[SourceConnectionResponse])
def list_connections(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(SourceSystemConnection).where(SourceSystemConnection.tenant_id == ctx.tenant.id)
    ).all()
    return [
        SourceConnectionResponse(
            id=r.id,
            system_type=r.system_type,
            display_name=r.display_name,
            status=r.status,
            last_sync_at=r.last_sync_at.isoformat() if r.last_sync_at else None,
        )
        for r in rows
    ]
