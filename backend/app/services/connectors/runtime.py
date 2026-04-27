from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.ai_settings_crypto import decrypt_settings_payload, encrypt_settings_payload, redact_settings_for_api
from app.models.entities import ConnectorMappingReview, IntegrationSyncRun, SourceEntityMapping, SourceSystemConnection
from app.services.connectors.onboarding import LIFECYCLE_STATES, SYNC_BEHAVIORS
from app.services.connectors.registry import ConnectorRegistry


class ConnectorRuntimeService:
    def __init__(self, db: Session):
        self.db = db
        self.registry = ConnectorRegistry()

    def _adapter_for_system(self, system_type: str):
        try:
            return self.registry.get(system_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported connector system type.",
            ) from exc

    def list_connections(self, tenant_id: UUID) -> list[SourceSystemConnection]:
        stmt = select(SourceSystemConnection).where(SourceSystemConnection.tenant_id == tenant_id)
        return list(self.db.scalars(stmt).all())

    def get_connection(self, tenant_id: UUID, connection_id: UUID) -> SourceSystemConnection:
        stmt = select(SourceSystemConnection).where(
            SourceSystemConnection.tenant_id == tenant_id,
            SourceSystemConnection.id == connection_id,
        )
        row = self.db.scalars(stmt).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
        return row

    def create_or_update_connection(
        self,
        *,
        tenant_id: UUID,
        connection_id: UUID | None,
        system_type: str,
        display_name: str,
        base_url: str | None,
        auth_mode: str,
        is_enabled: bool,
        sync_cadence_minutes: int,
        config_payload: dict,
    ) -> SourceSystemConnection:
        adapter = self._adapter_for_system(system_type)
        manifest = adapter.describe()
        if auth_mode not in manifest.auth_modes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported auth_mode '{auth_mode}' for connector '{system_type}'",
            )
        effective_config = dict(config_payload or {})
        if base_url and not effective_config.get("base_url"):
            effective_config["base_url"] = base_url
        missing = adapter.validate_config(auth_mode, effective_config)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing connector config keys: {', '.join(missing)}",
            )
        row: SourceSystemConnection | None = None
        if connection_id:
            row = self.get_connection(tenant_id, connection_id)
        if not row:
            row = SourceSystemConnection(
                tenant_id=tenant_id,
                system_type=system_type,
                provider_family=system_type,
                display_name=display_name,
                base_url=base_url,
                auth_mode=auth_mode,
                status="disconnected",
                is_enabled=is_enabled,
                health_status="unknown",
                sync_mode="manual_and_scheduled",
                sync_cadence_minutes=max(5, sync_cadence_minutes),
                lifecycle_state="configured",
                sync_behavior="manual_sync_only",
                is_paused=False,
                import_scope_mode="all",
                connector_version=manifest.connector_version,
                connection_metadata={
                    "supports_entities": list(manifest.capabilities),
                    "maturity": manifest.maturity,
                    "auth_modes": list(manifest.auth_modes),
                    "sync_modes": list(manifest.sync_modes),
                    "implemented": manifest.implemented,
                },
            )
            self.db.add(row)
        else:
            row.display_name = display_name
            row.base_url = base_url
            row.auth_mode = auth_mode
            row.is_enabled = is_enabled
            row.sync_cadence_minutes = max(5, sync_cadence_minutes)
            row.provider_family = system_type
            row.connector_version = manifest.connector_version
            row.lifecycle_state = row.lifecycle_state or "configured"
            row.sync_behavior = row.sync_behavior or "manual_sync_only"
            row.import_scope_mode = row.import_scope_mode or "all"
            row.connection_metadata = {
                "supports_entities": list(manifest.capabilities),
                "maturity": manifest.maturity,
                "auth_modes": list(manifest.auth_modes),
                "sync_modes": list(manifest.sync_modes),
                "implemented": manifest.implemented,
            }

        row.encrypted_config = encrypt_settings_payload(config_payload) if config_payload else row.encrypted_config
        self.db.flush()
        return row

    def safe_decrypted_config(self, connection: SourceSystemConnection) -> dict | None:
        if not connection.encrypted_config:
            return None
        try:
            return redact_settings_for_api(decrypt_settings_payload(connection.encrypted_config))
        except ValueError:
            return {"error": "[invalid encrypted config]"}

    def _decrypted_config(self, connection: SourceSystemConnection) -> dict:
        if not connection.encrypted_config:
            return {}
        try:
            return decrypt_settings_payload(connection.encrypted_config)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stored integration config could not be decrypted.",
            ) from exc

    def test_connection(self, tenant_id: UUID, connection_id: UUID) -> SourceSystemConnection:
        row = self.get_connection(tenant_id, connection_id)
        adapter = self._adapter_for_system(row.system_type)
        try:
            result = adapter.test_connection(
                db=self.db,
                tenant_id=tenant_id,
                connection=row,
                config=self._decrypted_config(row),
            )
        except Exception:
            from app.services.connectors.types import ConnectorTestResult

            result = ConnectorTestResult(
                ok=False,
                message="Connection test failed. Verify connector settings and try again.",
                checked_at=datetime.now(UTC),
            )
        row.last_tested_at = result.checked_at
        row.test_status = "succeeded" if result.ok else "failed"
        row.test_message = result.message
        row.health_status = "healthy" if result.ok else "error"
        row.status = "connected" if result.ok else "disconnected"
        row.lifecycle_state = "tested" if result.ok and row.lifecycle_state == "configured" else row.lifecycle_state
        row.last_error = None if result.ok else result.message
        self.db.flush()
        return row

    def trigger_sync(self, tenant_id: UUID, connection_id: UUID, *, trigger_mode: str = "manual") -> IntegrationSyncRun:
        connection = self.get_connection(tenant_id, connection_id)
        if not connection.is_enabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connection is disabled")
        if connection.is_paused:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connection sync is paused")
        if trigger_mode != "manual" and connection.sync_behavior == "manual_sync_only":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connection is manual-sync-only")
        now = datetime.now(UTC)
        run = IntegrationSyncRun(
            tenant_id=tenant_id,
            source_connection_id=connection.id,
            trigger_mode=trigger_mode,
            status="running",
            records_processed=0,
            started_at=now,
        )
        self.db.add(run)
        self.db.flush()

        adapter = self._adapter_for_system(connection.system_type)
        config = self._decrypted_config(connection)
        cursor = None
        if connection.connection_metadata and connection.connection_metadata.get("last_cursor"):
            cursor = str(connection.connection_metadata["last_cursor"])
        try:
            result = adapter.run_sync(
                db=self.db,
                tenant_id=tenant_id,
                connection=connection,
                config=config,
                cursor=cursor,
            )
        except Exception:
            from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats

            result = ConnectorSyncResult(
                ok=False,
                message="Connector sync failed unexpectedly. Check connector settings and try again.",
                completed_at=datetime.now(UTC),
                next_cursor=cursor,
                stats=ConnectorSyncStats(),
            )
        run.status = "succeeded" if result.ok else "failed"
        run.records_processed = result.stats.records_processed
        run.completed_at = result.completed_at
        run.error_summary = None if result.ok else result.message
        run.sync_cursor = result.next_cursor
        run.stats_json = result.stats.as_dict()

        connection.last_attempted_sync_at = now
        if result.ok:
            connection.last_sync_at = result.completed_at
            connection.last_successful_sync_at = result.completed_at
            connection.status = "connected"
            connection.health_status = "healthy"
            connection.last_error = None
            if connection.lifecycle_state in {"configured", "tested", "paused"}:
                connection.lifecycle_state = "active"
            meta = dict(connection.connection_metadata or {})
            meta["last_cursor"] = result.next_cursor
            connection.connection_metadata = meta
        else:
            connection.last_failed_sync_at = result.completed_at
            connection.health_status = "error"
            connection.last_error = result.message
            connection.status = "degraded"
            connection.lifecycle_state = "error"
        self.db.flush()
        return run

    def update_lifecycle(
        self,
        tenant_id: UUID,
        connection_id: UUID,
        *,
        actor_user_id: UUID | None,
        lifecycle_state: str | None,
        is_enabled: bool | None,
        is_paused: bool | None,
        sync_behavior: str | None,
        note: str | None,
    ) -> SourceSystemConnection:
        row = self.get_connection(tenant_id, connection_id)
        if lifecycle_state is not None and lifecycle_state not in LIFECYCLE_STATES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported lifecycle_state")
        if sync_behavior is not None and sync_behavior not in SYNC_BEHAVIORS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sync_behavior")
        if is_enabled is not None:
            row.is_enabled = is_enabled
        if is_paused is not None:
            row.is_paused = is_paused
        if lifecycle_state is not None:
            row.lifecycle_state = lifecycle_state
        if sync_behavior is not None:
            row.sync_behavior = sync_behavior
        row.last_lifecycle_changed_at = datetime.now(UTC)
        row.last_lifecycle_note = note
        return row

    def update_import_scope(
        self,
        tenant_id: UUID,
        connection_id: UUID,
        *,
        actor_user_id: UUID | None,
        import_scope_mode: str,
        filters: dict,
    ) -> SourceSystemConnection:
        row = self.get_connection(tenant_id, connection_id)
        adapter = self._adapter_for_system(row.system_type)
        manifest = adapter.describe()
        if import_scope_mode not in manifest.import_scope_modes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Import scope mode '{import_scope_mode}' not supported by connector '{row.system_type}'",
            )
        unknown_keys = [k for k in (filters or {}).keys() if k not in set(manifest.import_scope_filter_keys)]
        if unknown_keys:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported import scope filters: {', '.join(unknown_keys)}")
        row.import_scope_mode = import_scope_mode
        row.import_scope_filters = filters or {}
        row.last_lifecycle_changed_at = datetime.now(UTC)
        return row

    def list_sync_runs(self, tenant_id: UUID, connection_id: UUID, limit: int = 20) -> list[IntegrationSyncRun]:
        self.get_connection(tenant_id, connection_id)
        stmt = (
            select(IntegrationSyncRun)
            .where(
                IntegrationSyncRun.tenant_id == tenant_id,
                IntegrationSyncRun.source_connection_id == connection_id,
            )
            .order_by(IntegrationSyncRun.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def coverage_summary(self, tenant_id: UUID) -> dict:
        connections = self.list_connections(tenant_id)
        items: list[dict] = []
        unresolved_total = 0
        weak_total = 0
        phased = 0
        for c in connections:
            linked = self.db.scalar(
                select(func.count(func.distinct(SourceEntityMapping.canonical_entity_id))).where(
                    SourceEntityMapping.tenant_id == tenant_id,
                    SourceEntityMapping.source_connection_id == c.id,
                    SourceEntityMapping.entity_type == "customer",
                )
            ) or 0
            unresolved = self.db.scalar(
                select(func.count()).where(
                    ConnectorMappingReview.tenant_id == tenant_id,
                    ConnectorMappingReview.source_connection_id == c.id,
                    ConnectorMappingReview.status == "pending",
                )
            ) or 0
            weak = self.db.scalar(
                select(func.count()).where(
                    ConnectorMappingReview.tenant_id == tenant_id,
                    ConnectorMappingReview.source_connection_id == c.id,
                    ConnectorMappingReview.suggested_confidence == "medium",
                    ConnectorMappingReview.status == "pending",
                )
            ) or 0
            unresolved_total += int(unresolved)
            weak_total += int(weak)
            if c.import_scope_mode != "all":
                phased += 1
            items.append(
                {
                    "source_connection_id": c.id,
                    "source_connection_name": c.display_name,
                    "system_type": c.system_type,
                    "lifecycle_state": c.lifecycle_state,
                    "import_scope_mode": c.import_scope_mode,
                    "linked_customers": int(linked),
                    "unresolved_mappings": int(unresolved),
                    "weak_mappings": int(weak),
                }
            )
        return {
            "connected_systems": len(connections),
            "unresolved_mappings": unresolved_total,
            "weak_mappings": weak_total,
            "phased_onboarding_connections": phased,
            "items": items,
        }
