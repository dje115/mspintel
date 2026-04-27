from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.models.entities import Customer, SourceSystemConnection
from app.schemas.integrations import (
    ConnectionImportScopeUpdateRequest,
    ConnectionLifecycleUpdateRequest,
    ConnectorCatalogItem,
    IntegrationCoverageResponse,
    IntegrationSyncRunResponse,
    MappingReviewActionRequest,
    MappingReviewRow,
    SourceConnectionResponse,
    SourceConnectionUpsertRequest,
)
from app.services.connectors.onboarding import ConnectorOnboardingService
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
            system_type=m.key,
            display_name=m.display_name,
            description=m.description,
            system_family=m.system_family,
            maturity=m.maturity,
            supported_auth_modes=list(m.auth_modes),
            supports_entities=list(m.capabilities),
            supported_sync_modes=list(m.sync_modes),
            implemented=m.implemented,
            default_cadence_minutes=m.default_cadence_minutes,
            connector_version=m.connector_version,
            ui_help_text=m.ui_help_text,
            import_scope_modes=list(m.import_scope_modes),
            import_scope_filter_keys=list(m.import_scope_filter_keys),
            config_fields=[
                {
                    "key": f.key,
                    "label": f.label,
                    "required": f.required,
                    "secret": f.secret,
                    "editable_after_create": f.editable_after_create,
                    "help_text": f.help_text,
                }
                for f in m.config_fields
            ],
        )
        for m in svc.registry.list_manifests()
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


@router.patch("/connections/{connection_id}/lifecycle", response_model=SourceConnectionResponse)
def update_connection_lifecycle(
    connection_id: str,
    body: ConnectionLifecycleUpdateRequest,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    svc = ConnectorRuntimeService(db)
    row = svc.update_lifecycle(
        ctx.tenant.id,
        UUID(connection_id),
        actor_user_id=ctx.user.id,
        lifecycle_state=body.lifecycle_state,
        is_enabled=body.is_enabled,
        is_paused=body.is_paused,
        sync_behavior=body.sync_behavior,
        note=body.note,
    )
    onboarding = ConnectorOnboardingService(db)
    onboarding.audit(
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        event_type="connector_lifecycle_updated",
        details=f"connection_id={row.id}; state={row.lifecycle_state}; paused={row.is_paused}; enabled={row.is_enabled}",
    )
    db.commit()
    db.refresh(row)
    return _to_connection_response(svc, row)


@router.patch("/connections/{connection_id}/import-scope", response_model=SourceConnectionResponse)
def update_connection_import_scope(
    connection_id: str,
    body: ConnectionImportScopeUpdateRequest,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    svc = ConnectorRuntimeService(db)
    row = svc.update_import_scope(
        ctx.tenant.id,
        UUID(connection_id),
        actor_user_id=ctx.user.id,
        import_scope_mode=body.import_scope_mode,
        filters=body.filters,
    )
    onboarding = ConnectorOnboardingService(db)
    onboarding.audit(
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        event_type="connector_import_scope_updated",
        details=f"connection_id={row.id}; mode={row.import_scope_mode}",
    )
    db.commit()
    db.refresh(row)
    return _to_connection_response(svc, row)


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


@router.get("/coverage", response_model=IntegrationCoverageResponse)
def integration_coverage(
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    svc = ConnectorRuntimeService(db)
    return IntegrationCoverageResponse(**svc.coverage_summary(ctx.tenant.id))


@router.get("/mappings", response_model=list[MappingReviewRow])
def list_mapping_reviews(
    connection_id: str | None = None,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    svc = ConnectorOnboardingService(db)
    rows = svc.list_mapping_reviews(ctx.tenant.id, UUID(connection_id) if connection_id else None)
    conn_map = {
        c.id: c.display_name for c in ConnectorRuntimeService(db).list_connections(ctx.tenant.id)
    }
    customers = {c.id: c.name for c in db.scalars(select(Customer).where(Customer.tenant_id == ctx.tenant.id)).all()}
    return [
        MappingReviewRow(
            id=r.id,
            source_connection_id=r.source_connection_id,
            source_connection_name=conn_map.get(r.source_connection_id),
            entity_type=r.entity_type,
            source_external_id=r.source_external_id,
            source_display_name=r.source_display_name,
            source_domain=r.source_domain,
            suggested_customer_id=r.suggested_customer_id,
            suggested_customer_name=customers.get(r.suggested_customer_id),
            suggested_confidence=r.suggested_confidence,
            suggested_score=float(r.suggested_score) if r.suggested_score is not None else None,
            suggested_reasons=list(r.suggested_reasons or []),
            status=r.status,
            mapped_customer_id=r.mapped_customer_id,
            mapped_customer_name=customers.get(r.mapped_customer_id),
            reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
            notes=r.notes,
        )
        for r in rows
    ]


@router.post("/mappings/{review_id}/action", response_model=MappingReviewRow)
def mapping_review_action(
    review_id: str,
    body: MappingReviewActionRequest,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    svc = ConnectorOnboardingService(db)
    row = svc.apply_mapping_action(
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        review_id=UUID(review_id),
        action=body.action,
        customer_id=body.customer_id,
        notes=body.notes,
    )
    db.commit()
    db.refresh(row)
    customer_names = {c.id: c.name for c in db.scalars(select(Customer).where(Customer.tenant_id == ctx.tenant.id)).all()}
    connection_name = db.scalars(
        select(SourceSystemConnection.display_name).where(
            SourceSystemConnection.tenant_id == ctx.tenant.id, SourceSystemConnection.id == row.source_connection_id
        )
    ).first()
    return MappingReviewRow(
        id=row.id,
        source_connection_id=row.source_connection_id,
        source_connection_name=connection_name,
        entity_type=row.entity_type,
        source_external_id=row.source_external_id,
        source_display_name=row.source_display_name,
        source_domain=row.source_domain,
        suggested_customer_id=row.suggested_customer_id,
        suggested_customer_name=customer_names.get(row.suggested_customer_id),
        suggested_confidence=row.suggested_confidence,
        suggested_score=float(row.suggested_score) if row.suggested_score is not None else None,
        suggested_reasons=list(row.suggested_reasons or []),
        status=row.status,
        mapped_customer_id=row.mapped_customer_id,
        mapped_customer_name=customer_names.get(row.mapped_customer_id),
        reviewed_at=row.reviewed_at.isoformat() if row.reviewed_at else None,
        notes=row.notes,
    )
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
        lifecycle_state=r.lifecycle_state,
        sync_behavior=r.sync_behavior,
        is_paused=r.is_paused,
        import_scope_mode=r.import_scope_mode,
        import_scope_filters=r.import_scope_filters,
        last_lifecycle_changed_at=r.last_lifecycle_changed_at.isoformat() if r.last_lifecycle_changed_at else None,
        last_lifecycle_note=r.last_lifecycle_note,
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
