from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import SourceSystemConnection
from app.services.connectors.manifest import ConnectorManifest
from app.services.connectors.types import ConnectorSyncResult, ConnectorTestResult


class ConnectorAdapter(ABC):
    manifest: ConnectorManifest

    @property
    def system_type(self) -> str:
        return self.manifest.key

    @property
    def display_name(self) -> str:
        return self.manifest.display_name

    @property
    def supports_entities(self) -> tuple[str, ...]:
        return self.manifest.capabilities

    @property
    def default_cadence_minutes(self) -> int:
        return self.manifest.default_cadence_minutes

    @property
    def connector_version(self) -> str:
        return self.manifest.connector_version

    def describe(self) -> ConnectorManifest:
        return self.manifest

    def validate_config(self, auth_mode: str, config: dict) -> list[str]:
        """Default strict config validation from manifest metadata."""
        missing: list[str] = []
        for key in self.manifest.required_fields_for_auth(auth_mode):
            if not config.get(key):
                missing.append(key)
        return missing

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
