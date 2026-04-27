from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import SourceSystemConnection
from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.manifest import ConnectorConfigField, ConnectorManifest
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult


class UnsupportedConnectorAdapter(ConnectorAdapter):
    def __init__(
        self,
        *,
        system_type: str,
        display_name: str,
        supports_entities: tuple[str, ...],
        message: str,
        maturity: str = "stub",
        auth_modes: tuple[str, ...] = ("api_key",),
        sync_modes: tuple[str, ...] = ("manual",),
    ) -> None:
        self.manifest = ConnectorManifest(
            key=system_type,
            display_name=display_name,
            description=message,
            system_family=system_type,
            maturity=maturity,  # type: ignore[arg-type]
            auth_modes=auth_modes,  # type: ignore[arg-type]
            capabilities=supports_entities,
            sync_modes=sync_modes,  # type: ignore[arg-type]
            implemented=False,
            connector_version="v1",
            config_fields=(ConnectorConfigField(key="note", label="Notes", required=False, secret=False),),
            ui_help_text=message,
        )
        self._message = message

    def test_connection(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
    ) -> ConnectorTestResult:
        return ConnectorTestResult(ok=False, message=self._message, checked_at=datetime.now(UTC))

    def run_sync(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
        cursor: str | None,
    ) -> ConnectorSyncResult:
        return ConnectorSyncResult(
            ok=False,
            message=self._message,
            completed_at=datetime.now(UTC),
            next_cursor=cursor,
            stats=ConnectorSyncStats(warnings=[self._message]),
        )
