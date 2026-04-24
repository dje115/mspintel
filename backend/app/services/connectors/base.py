from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import SourceSystemConnection
from app.services.connectors.types import ConnectorSyncResult, ConnectorTestResult


class ConnectorAdapter(ABC):
    system_type: str
    display_name: str
    supports_entities: tuple[str, ...]
    default_cadence_minutes: int = 60
    connector_version: str = "v1"

    @abstractmethod
    def test_connection(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
    ) -> ConnectorTestResult: ...

    @abstractmethod
    def run_sync(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
        cursor: str | None,
    ) -> ConnectorSyncResult: ...
