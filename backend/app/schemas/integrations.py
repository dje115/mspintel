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
    supports_entities: list[str]
    default_cadence_minutes: int
    connector_version: str
