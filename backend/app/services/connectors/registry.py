from __future__ import annotations

from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.capabilities import (
    CAP_ACTIVITIES,
    CAP_BACKUP_JOBS,
    CAP_BILLING_ACCOUNTS,
    CAP_CALL_LOGS,
    CAP_CONTACTS,
    CAP_CONTRACTS,
    CAP_CUSTOMERS,
    CAP_INVOICES,
    CAP_LICENCES,
    CAP_MAILBOXES,
    CAP_NOTES,
    CAP_OPPORTUNITIES,
    CAP_QUOTES,
    CAP_STORAGE,
    CAP_TICKETS,
    CAP_USERS,
)
from app.services.connectors.constants import (
    CONNECTOR_SYSTEM_AUTOTASK,
    CONNECTOR_SYSTEM_AZURE,
    CONNECTOR_SYSTEM_3CX,
    CONNECTOR_SYSTEM_CONNECTWISE,
    CONNECTOR_SYSTEM_ENTRA,
    CONNECTOR_SYSTEM_ITQUOTER,
    CONNECTOR_SYSTEM_MICROSOFT_365,
    CONNECTOR_SYSTEM_SAGE,
    CONNECTOR_SYSTEM_VEEAM,
    CONNECTOR_SYSTEM_XERO,
)
from app.services.connectors.providers.autotask import AutotaskConnectorAdapter
from app.services.connectors.providers.microsoft_365 import Microsoft365ConnectorAdapter
from app.services.connectors.providers.stubs import UnsupportedConnectorAdapter
from app.services.connectors.providers.xero import XeroConnectorAdapter


class ConnectorRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ConnectorAdapter] = {
            CONNECTOR_SYSTEM_AUTOTASK: AutotaskConnectorAdapter(),
            CONNECTOR_SYSTEM_ITQUOTER: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_ITQUOTER,
                display_name="ITQuoter",
                supports_entities=(CAP_QUOTES, CAP_OPPORTUNITIES, CAP_ACTIVITIES),
                message="ITQuoter adapter is scaffolded but not implemented in this release.",
                maturity="stub",
                auth_modes=("api_key",),
                sync_modes=("manual",),
            ),
            CONNECTOR_SYSTEM_CONNECTWISE: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_CONNECTWISE,
                display_name="ConnectWise",
                supports_entities=(CAP_CUSTOMERS, CAP_CONTACTS, CAP_TICKETS, CAP_OPPORTUNITIES, CAP_CONTRACTS, CAP_NOTES),
                message="ConnectWise adapter is planned for a future connector pack.",
                maturity="planned",
                auth_modes=("api_key",),
                sync_modes=("manual", "delta"),
            ),
            CONNECTOR_SYSTEM_VEEAM: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_VEEAM,
                display_name="Veeam",
                supports_entities=(CAP_BACKUP_JOBS, CAP_CONTRACTS, CAP_ACTIVITIES),
                message="Veeam adapter is planned for service/backup ingestion in a future release.",
                maturity="planned",
                auth_modes=("username_password", "token_endpoint"),
                sync_modes=("manual", "delta"),
            ),
            CONNECTOR_SYSTEM_XERO: XeroConnectorAdapter(),
            CONNECTOR_SYSTEM_SAGE: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_SAGE,
                display_name="Sage",
                supports_entities=(CAP_BILLING_ACCOUNTS, CAP_INVOICES),
                message="Sage accounting adapter is planned for a future release.",
                maturity="planned",
                auth_modes=("oauth2", "api_key"),
                sync_modes=("manual", "delta"),
            ),
            CONNECTOR_SYSTEM_MICROSOFT_365: Microsoft365ConnectorAdapter(),
            CONNECTOR_SYSTEM_ENTRA: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_ENTRA,
                display_name="Entra ID",
                supports_entities=(CAP_USERS, CAP_LICENCES, CAP_ACTIVITIES),
                message="Entra connector is planned for identity/risk enrichment.",
                maturity="planned",
                auth_modes=("oauth2",),
                sync_modes=("manual", "delta"),
            ),
            CONNECTOR_SYSTEM_AZURE: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_AZURE,
                display_name="Azure",
                supports_entities=(CAP_ACTIVITIES, CAP_NOTES),
                message="Azure connector is planned for cloud/commercial insights.",
                maturity="planned",
                auth_modes=("oauth2",),
                sync_modes=("manual", "delta"),
            ),
            CONNECTOR_SYSTEM_3CX: UnsupportedConnectorAdapter(
                system_type=CONNECTOR_SYSTEM_3CX,
                display_name="3CX / Telephony",
                supports_entities=(CAP_CALL_LOGS, CAP_ACTIVITIES, CAP_NOTES),
                message="3CX connector is planned for relationship and cadence signals.",
                maturity="planned",
                auth_modes=("api_key", "token_endpoint"),
                sync_modes=("manual", "delta"),
            ),
        }

    def get(self, system_type: str) -> ConnectorAdapter:
        adapter = self._adapters.get(system_type)
        if not adapter:
            raise ValueError(f"Unsupported connector system: {system_type}")
        return adapter

    def list_adapters(self) -> list[ConnectorAdapter]:
        return list(self._adapters.values())

    def list_manifests(self):
        return [a.describe() for a in self.list_adapters()]

    def get_manifest(self, system_type: str):
        return self.get(system_type).describe()
