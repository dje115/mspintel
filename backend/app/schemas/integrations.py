from uuid import UUID

from pydantic import BaseModel, Field


class SourceConnectionUpsertRequest(BaseModel):
    system_type: str
    display_name: str
    base_url: str | None = None
    auth_mode: str = "api_key"
    is_enabled: bool = True
    sync_cadence_minutes: int = Field(default=60, ge=5, le=1440)
    config: dict = Field(default_factory=dict)


class ConnectionLifecycleUpdateRequest(BaseModel):
    lifecycle_state: str | None = None
    is_enabled: bool | None = None
    is_paused: bool | None = None
    sync_behavior: str | None = None
    note: str | None = None


class ConnectionImportScopeUpdateRequest(BaseModel):
    import_scope_mode: str
    filters: dict = Field(default_factory=dict)


class SourceConnectionResponse(BaseModel):
    id: UUID
    system_type: str
    provider_family: str
    display_name: str
    base_url: str | None
    auth_mode: str
    status: str
    is_enabled: bool
    health_status: str
    test_status: str | None
    test_message: str | None
    last_error: str | None
    sync_cadence_minutes: int
    sync_mode: str
    connector_version: str
    connection_metadata: dict | None
    safe_config: dict | None
    lifecycle_state: str
    sync_behavior: str
    is_paused: bool
    import_scope_mode: str
    import_scope_filters: dict | None
    last_lifecycle_changed_at: str | None
    last_lifecycle_note: str | None
    last_tested_at: str | None
    last_attempted_sync_at: str | None
    last_successful_sync_at: str | None
    last_failed_sync_at: str | None
    last_sync_at: str | None


class IntegrationSyncRunResponse(BaseModel):
    id: UUID
    source_connection_id: UUID
    trigger_mode: str
    status: str
    records_processed: int
    started_at: str | None
    completed_at: str | None
    error_summary: str | None
    sync_cursor: str | None
    stats_json: dict | None


class ConnectorCatalogItem(BaseModel):
    system_type: str
    display_name: str
    description: str
    system_family: str
    maturity: str
    supported_auth_modes: list[str]
    supports_entities: list[str]
    supported_sync_modes: list[str]
    implemented: bool
    default_cadence_minutes: int
    connector_version: str
    ui_help_text: str | None = None
    import_scope_modes: list[str] = Field(default_factory=list)
    import_scope_filter_keys: list[str] = Field(default_factory=list)
    config_fields: list[dict] = Field(default_factory=list)


class MappingReviewRow(BaseModel):
    id: UUID
    source_connection_id: UUID
    source_connection_name: str | None = None
    source_system_key: str | None = None
    entity_type: str
    source_external_id: str
    source_display_name: str | None = None
    source_domain: str | None = None
    suggested_customer_id: UUID | None = None
    suggested_customer_name: str | None = None
    suggested_confidence: str
    suggested_score: float | None = None
    suggested_reasons: list[str] = Field(default_factory=list)
    status: str
    status_label: str | None = None
    mapped_customer_id: UUID | None = None
    mapped_customer_name: str | None = None
    last_sync_run_id: UUID | None = None
    last_sync_status: str | None = None
    last_sync_started_at: str | None = None
    reviewed_at: str | None = None
    notes: str | None = None
    eligible_for_customer_create: bool = False
    create_customer_blockers: list[str] = Field(default_factory=list)


class MappingReviewActionRequest(BaseModel):
    action: str
    customer_id: UUID | None = None
    notes: str | None = None


class MappingCreateCustomersRequest(BaseModel):
    review_ids: list[UUID] = Field(default_factory=list)
    connection_id: UUID | None = None


class MappingCreateCustomersResponse(BaseModel):
    requested_rows: int
    eligible_rows: int
    created_customers: int
    accepted_rows: int
    skipped_rows: int
    created_customer_ids: list[UUID] = Field(default_factory=list)
    updated_review_ids: list[UUID] = Field(default_factory=list)


class IntegrationCoverageItem(BaseModel):
    source_connection_id: UUID
    source_connection_name: str
    system_type: str
    lifecycle_state: str
    import_scope_mode: str
    linked_customers: int
    unresolved_mappings: int
    weak_mappings: int


class IntegrationCoverageResponse(BaseModel):
    connected_systems: int
    unresolved_mappings: int
    weak_mappings: int
    phased_onboarding_connections: int
    items: list[IntegrationCoverageItem]
