from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.models.entities import ConnectorMappingReview, Customer, SourceSystemConnection
from app.schemas.integrations import (
    ConnectionImportScopeUpdateRequest,
    ConnectionLifecycleUpdateRequest,
    ConnectorCatalogItem,
    IntegrationCoverageResponse,
    IntegrationSyncRunResponse,
    MappingReviewActionRequest,
    MappingCreateCustomersRequest,
    MappingCreateCustomersResponse,
    MappingReviewRow,
    SourceConnectionResponse,
    SourceConnectionUpsertRequest,
)
from app.services.connectors.onboarding import ConnectorOnboardingService
from app.services.connectors.runtime import ConnectorRuntimeService

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

STATUS_LABELS = {
    "pending": "Needs review",
    "accepted": "Confirmed",
    "remapped": "Confirmed",
    "rejected": "Rejected",
    "unlinked": "Unlinked",
}


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
    status_filter: str | None = None,
    confidence: str | None = None,
    search: str | None = None,
    customer_id: str | None = None,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    svc = ConnectorOnboardingService(db)
    statuses = {s.strip() for s in (status_filter or "").split(",") if s.strip()} or None
    confidence_labels = {s.strip() for s in (confidence or "").split(",") if s.strip()} or None
    selected_customer = UUID(customer_id) if customer_id else None
    rows = svc.list_mapping_reviews(
        ctx.tenant.id,
        connection_id=UUID(connection_id) if connection_id else None,
        statuses=statuses,
        confidence_labels=confidence_labels,
        search=search,
        customer_id=selected_customer,
    )
    connections = ConnectorRuntimeService(db).list_connections(ctx.tenant.id)
    conn_map = {c.id: c for c in connections}
    latest_runs = svc.latest_sync_runs_by_connection(ctx.tenant.id, {r.source_connection_id for r in rows})
    customer_rows = list(db.scalars(select(Customer).where(Customer.tenant_id == ctx.tenant.id)).all())
    customer_names = {c.id: c.name for c in customer_rows}
    tenant_name_keys = {"".join(ch for ch in c.name.lower() if ch.isalnum()) for c in customer_rows if c.name}
    tenant_contact_domains: set[str] = set()
    return [
        _to_mapping_review_row(
            r,
            conn_map,
            customer_names,
            latest_runs,
            svc=svc,
            tenant_name_keys=tenant_name_keys,
            tenant_contact_domains=tenant_contact_domains,
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
    customer_rows = list(db.scalars(select(Customer).where(Customer.tenant_id == ctx.tenant.id)).all())
    customer_names = {c.id: c.name for c in customer_rows}
    connection = db.scalars(
        select(SourceSystemConnection).where(
            SourceSystemConnection.tenant_id == ctx.tenant.id, SourceSystemConnection.id == row.source_connection_id
        )
    ).first()
    latest_runs = svc.latest_sync_runs_by_connection(ctx.tenant.id, {row.source_connection_id})
    tenant_name_keys = {"".join(ch for ch in c.name.lower() if ch.isalnum()) for c in customer_rows if c.name}
    tenant_contact_domains = set()
    return _to_mapping_review_row(
        row,
        {row.source_connection_id: connection} if connection else {},
        customer_names,
        latest_runs,
        svc=svc,
        tenant_name_keys=tenant_name_keys,
        tenant_contact_domains=tenant_contact_domains,
    )


@router.post("/mappings/create-customers", response_model=MappingCreateCustomersResponse)
def create_customers_from_mappings(
    body: MappingCreateCustomersRequest,
    ctx: AccessContext = Depends(require_permission("membership:write")),
    db: Session = Depends(get_db),
):
    svc = ConnectorOnboardingService(db)
    result = svc.create_customers_from_mapping_reviews(
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        review_ids=list(body.review_ids or []),
        connection_id=body.connection_id,
    )
    db.commit()
    return MappingCreateCustomersResponse(
        requested_rows=result.requested_rows,
        eligible_rows=result.eligible_rows,
        created_customers=result.created_customers,
        accepted_rows=result.accepted_rows,
        skipped_rows=result.skipped_rows,
        created_customer_ids=result.created_customer_ids,
        updated_review_ids=result.updated_review_ids,
    )


def _to_mapping_review_row(
    r: ConnectorMappingReview,
    connection_map: dict[UUID, SourceSystemConnection],
    customer_names: dict[UUID, str],
    latest_runs: dict[UUID, object],
    svc: ConnectorOnboardingService,
    tenant_name_keys: set[str],
    tenant_contact_domains: set[str],
) -> MappingReviewRow:
    conn = connection_map.get(r.source_connection_id)
    last_run = latest_runs.get(r.source_connection_id)
    eligibility = svc.customer_create_eligibility(
        row=r,
        tenant_name_keys=tenant_name_keys,
        tenant_contact_domains=tenant_contact_domains,
    )
    return MappingReviewRow(
        id=r.id,
        source_connection_id=r.source_connection_id,
        source_connection_name=conn.display_name if conn else None,
        source_system_key=conn.system_type if conn else None,
        entity_type=r.entity_type,
        source_external_id=r.source_external_id,
        source_display_name=r.source_display_name,
        source_domain=r.source_domain,
        suggested_customer_id=r.suggested_customer_id,
        suggested_customer_name=customer_names.get(r.suggested_customer_id),
        suggested_confidence=r.suggested_confidence,
        suggested_score=float(r.suggested_score) if r.suggested_score is not None else None,
        suggested_reasons=list(r.suggested_reasons or []),
        status=r.status,
        status_label=STATUS_LABELS.get(r.status, r.status.title()),
        mapped_customer_id=r.mapped_customer_id,
        mapped_customer_name=customer_names.get(r.mapped_customer_id),
        last_sync_run_id=getattr(last_run, "id", None),
        last_sync_status=getattr(last_run, "status", None),
        last_sync_started_at=getattr(last_run, "started_at", None).isoformat() if getattr(last_run, "started_at", None) else None,
        reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
        notes=r.notes,
        eligible_for_customer_create=eligibility.eligible,
        create_customer_blockers=eligibility.blockers,
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
