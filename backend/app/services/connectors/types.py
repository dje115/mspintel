from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConnectorTestResult:
    ok: bool
    message: str
    checked_at: datetime
    metadata: dict | None = None


@dataclass
class ConnectorSyncStats:
    customers_upserted: int = 0
    contacts_upserted: int = 0
    tickets_upserted: int = 0
    opportunities_upserted: int = 0
    quotes_upserted: int = 0
    mappings_written: int = 0
    finance_billing_accounts_upserted: int = 0
    finance_invoices_upserted: int = 0
    finance_snapshots_upserted: int = 0
    m365_postures_upserted: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "customers_upserted": self.customers_upserted,
            "contacts_upserted": self.contacts_upserted,
            "tickets_upserted": self.tickets_upserted,
            "opportunities_upserted": self.opportunities_upserted,
            "quotes_upserted": self.quotes_upserted,
            "mappings_written": self.mappings_written,
            "finance_billing_accounts_upserted": self.finance_billing_accounts_upserted,
            "finance_invoices_upserted": self.finance_invoices_upserted,
            "finance_snapshots_upserted": self.finance_snapshots_upserted,
            "m365_postures_upserted": self.m365_postures_upserted,
            "warnings": self.warnings,
        }

    @property
    def records_processed(self) -> int:
        return (
            self.customers_upserted
            + self.contacts_upserted
            + self.tickets_upserted
            + self.opportunities_upserted
            + self.quotes_upserted
            + self.finance_billing_accounts_upserted
            + self.finance_invoices_upserted
            + self.finance_snapshots_upserted
            + self.m365_postures_upserted
        )


@dataclass
class ConnectorSyncResult:
    ok: bool
    message: str
    completed_at: datetime
    next_cursor: str | None
    stats: ConnectorSyncStats
