from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import SourceSystemConnection
from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult


class UnsupportedConnectorAdapter(ConnectorAdapter):
    def __init__(
        self,
        *,
        system_type: str,
        display_name: str,
        supports_entities: tuple[str, ...],
        message: str,
    ) -> None:
        self.system_type = system_type
        self.display_name = display_name
        self.supports_entities = supports_entities
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
