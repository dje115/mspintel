from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.integrations import (
    ConnectorCatalogItem,
    IntegrationSyncRunResponse,
    SourceConnectionResponse,
    SourceConnectionUpsertRequest,
)
from app.services.connectors.runtime import ConnectorRuntimeService

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.get("/connections", response_model=list[SourceConnectionResponse])
def list_connections(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    svc = ConnectorRuntimeService(db)
    rows = svc.list_connections(ctx.tenant.id)
    return [_to_connection_response(svc, r) for r in rows]


@router.get("/catalog", response_model=list[ConnectorCatalogItem])
def connector_catalog(
    _: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    svc = ConnectorRuntimeService(db)
    return [
        ConnectorCatalogItem(
            system_type=a.system_type,
            display_name=a.display_name,
            supports_entities=list(a.supports_entities),
            default_cadence_minutes=a.default_cadence_minutes,
            connector_version=a.connector_version,
        )
        for a in svc.registry.list_adapters()
    ]


@router.post("/connections", response_model=SourceConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_connection(
    body: SourceConnectionUpsertRequest,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    svc = ConnectorRuntimeService(db)
    row = svc.create_or_update_connection(
        tenant_id=ctx.tenant.id,
        connection_id=None,
        system_type=body.system_type,
        display_name=body.display_name,
        base_url=body.base_url,
        auth_mode=body.auth_mode,
        is_enabled=body.is_enabled,
        sync_cadence_minutes=body.sync_cadence_minutes,
        config_payload=body.config,
    )
    db.commit()
    db.refresh(row)
    return _to_connection_response(svc, row)


@router.patch("/connections/{connection_id}", response_model=SourceConnectionResponse)
def update_connection(
    connection_id: str,
    body: SourceConnectionUpsertRequest,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    svc = ConnectorRuntimeService(db)
    row = svc.create_or_update_connection(
        tenant_id=ctx.tenant.id,
        connection_id=UUID(connection_id),
        system_type=body.system_type,
        display_name=body.display_name,
        base_url=body.base_url,
        auth_mode=body.auth_mode,
        is_enabled=body.is_enabled,
        sync_cadence_minutes=body.sync_cadence_minutes,
        config_payload=body.config,
    )
    db.commit()
    db.refresh(row)
    return _to_connection_response(svc, row)


@router.post("/connections/{connection_id}/test", response_model=SourceConnectionResponse)
def test_connection(
    connection_id: str,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    svc = ConnectorRuntimeService(db)
    row = svc.test_connection(ctx.tenant.id, UUID(connection_id))
    db.commit()
    db.refresh(row)
    return _to_connection_response(svc, row)


@router.post("/connections/{connection_id}/sync", response_model=IntegrationSyncRunResponse, status_code=status.HTTP_202_ACCEPTED)
def sync_connection(
    connection_id: str,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    svc = ConnectorRuntimeService(db)
    run = svc.trigger_sync(ctx.tenant.id, UUID(connection_id), trigger_mode="manual")
    db.commit()
    db.refresh(run)
    return _to_run_response(run)


@router.get("/connections/{connection_id}/runs", response_model=list[IntegrationSyncRunResponse])
def list_connection_runs(
    connection_id: str,
    limit: int = 20,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    svc = ConnectorRuntimeService(db)
    return [_to_run_response(r) for r in svc.list_sync_runs(ctx.tenant.id, UUID(connection_id), limit=limit)]


def _to_connection_response(svc: ConnectorRuntimeService, r) -> SourceConnectionResponse:
    return SourceConnectionResponse(
        id=r.id,
        system_type=r.system_type,
        provider_family=r.provider_family,
        display_name=r.display_name,
        base_url=r.base_url,
        auth_mode=r.auth_mode,
        status=r.status,
        is_enabled=r.is_enabled,
        health_status=r.health_status,
        test_status=r.test_status,
        test_message=r.test_message,
        last_error=r.last_error,
        sync_cadence_minutes=r.sync_cadence_minutes,
        sync_mode=r.sync_mode,
        connector_version=r.connector_version,
        connection_metadata=r.connection_metadata,
        safe_config=svc.safe_decrypted_config(r),
        last_tested_at=r.last_tested_at.isoformat() if r.last_tested_at else None,
        last_attempted_sync_at=r.last_attempted_sync_at.isoformat() if r.last_attempted_sync_at else None,
        last_successful_sync_at=r.last_successful_sync_at.isoformat() if r.last_successful_sync_at else None,
        last_failed_sync_at=r.last_failed_sync_at.isoformat() if r.last_failed_sync_at else None,
        last_sync_at=r.last_sync_at.isoformat() if r.last_sync_at else None,
    )


def _to_run_response(run) -> IntegrationSyncRunResponse:
    return IntegrationSyncRunResponse(
        id=run.id,
        source_connection_id=run.source_connection_id,
        trigger_mode=run.trigger_mode,
        status=run.status,
        records_processed=run.records_processed,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        error_summary=run.error_summary,
        sync_cursor=run.sync_cursor,
        stats_json=run.stats_json,
    )
