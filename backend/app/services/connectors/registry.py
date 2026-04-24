from __future__ import annotations

from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.constants import (
    CONNECTOR_SYSTEM_AUTOTASK,
    CONNECTOR_SYSTEM_CONNECTWISE,
    CONNECTOR_SYSTEM_ITQUOTER,
    CONNECTOR_SYSTEM_VEEAM,
)
from app.services.connectors.providers.autotask import AutotaskConnectorAdapter
from app.services.connectors.providers.stubs import UnsupportedConnectorAdapter


class ConnectorRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ConnectorAdapter] = {
            CONNECTOR_SYSTEM_AUTOTASK: AutotaskConnectorAdapter(),
            CONNECTOR_SYSTEM_ITQUOTER: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_ITQUOTER,
                display_name="ITQuoter",
                supports_entities=("quote", "opportunity", "activity"),
                message="ITQuoter adapter is scaffolded but not implemented in this release.",
            ),
            CONNECTOR_SYSTEM_CONNECTWISE: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_CONNECTWISE,
                display_name="ConnectWise",
                supports_entities=("customer", "contact", "ticket", "opportunity", "agreement"),
                message="ConnectWise adapter is planned for a future connector pack.",
            ),
            CONNECTOR_SYSTEM_VEEAM: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_VEEAM,
                display_name="Veeam",
                supports_entities=("activity", "service", "backup"),
                message="Veeam adapter is planned for service/backup ingestion in a future release.",
            ),
        }

    def get(self, system_type: str) -> ConnectorAdapter:
        adapter = self._adapters.get(system_type)
        if not adapter:
            raise ValueError(f"Unsupported connector system: {system_type}")
        return adapter

    def list_adapters(self) -> list[ConnectorAdapter]:
        return list(self._adapters.values())
