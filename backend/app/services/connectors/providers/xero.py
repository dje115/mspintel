from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer, FinanceInvoice, SourceEntityMapping, SourceSystemConnection
from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.constants import (
    CONNECTOR_SYSTEM_XERO,
    ENTITY_FINANCE_BILLING_ACCOUNT,
    ENTITY_FINANCE_INVOICE,
)
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult
from app.services.finance_canonical import upsert_finance_for_customer


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


class XeroConnectorAdapter(ConnectorAdapter):
    """Thin read-only finance path: demo/sandbox uses canonical upsert from in-app profile data.

    Live Xero invoice APIs are intentionally out of scope for Finance Phase 0; non-demo sync records a clear warning.
    """

    system_type = CONNECTOR_SYSTEM_XERO
    display_name = "Xero (accounting)"
    supports_entities = (ENTITY_FINANCE_BILLING_ACCOUNT, ENTITY_FINANCE_INVOICE)
    default_cadence_minutes = 360
    connector_version = "finance_v0"

    def _is_demo_mode(self, config: dict) -> bool:
        return bool(config.get("demo_mode")) or str(config.get("sandbox") or "").lower() in ("1", "true", "yes")

    def _oauth_fields_present(self, config: dict) -> bool:
        return all(
            bool(str(config.get(k) or "").strip())
            for k in ("client_id", "client_secret", "refresh_token", "xero_tenant_id")
        )

    def test_connection(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
    ) -> ConnectorTestResult:
        if self._is_demo_mode(config):
            return ConnectorTestResult(
                ok=True,
                message="Demo/sandbox mode: finance facts sync from in-app customer profiles (no live Xero API calls).",
                checked_at=datetime.now(UTC),
                metadata={"mode": "demo_profile"},
            )
        if self._oauth_fields_present(config):
            return ConnectorTestResult(
                ok=True,
                message="OAuth configuration present. Live Xero read sync is not enabled in Finance Phase 0 — use demo_mode for sample data.",
                checked_at=datetime.now(UTC),
                metadata={"mode": "credentials_only"},
            )
        return ConnectorTestResult(
            ok=False,
            message="Configure demo_mode: true for sandbox finance sync, or supply client_id, client_secret, refresh_token, and xero_tenant_id for future live reads.",
            checked_at=datetime.now(UTC),
        )

    def _upsert_mapping(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        source_connection_id: UUID,
        entity_type: str,
        source_id: str,
        canonical_entity_id: UUID,
    ) -> None:
        stmt = select(SourceEntityMapping).where(
            SourceEntityMapping.tenant_id == tenant_id,
            SourceEntityMapping.source_connection_id == source_connection_id,
            SourceEntityMapping.entity_type == entity_type,
            SourceEntityMapping.source_id == source_id,
        )
        row = db.scalars(stmt).first()
        if row:
            row.canonical_entity_id = canonical_entity_id
            row.source_updated_at = datetime.now(UTC)
        else:
            db.add(
                SourceEntityMapping(
                    tenant_id=tenant_id,
                    source_connection_id=source_connection_id,
                    entity_type=entity_type,
                    source_id=source_id,
                    canonical_entity_id=canonical_entity_id,
                    source_updated_at=datetime.now(UTC),
                )
            )

    def run_sync(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
        cursor: str | None,
    ) -> ConnectorSyncResult:
        stats = ConnectorSyncStats()
        now = datetime.now(UTC)
        if self._is_demo_mode(config):
            stmt = select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.name)
            customers = list(db.scalars(stmt).all())
            for cust in customers:
                acct = upsert_finance_for_customer(
                    db,
                    tenant_id=tenant_id,
                    customer_id=cust.id,
                    customer_name=cust.name,
                    demo_profile=cust.demo_profile,
                    source_connection_id=connection.id,
                    provenance="xero_connector_demo",
                )
                if not acct:
                    continue
                stats.finance_billing_accounts_upserted += 1
                stats.finance_snapshots_upserted += 1
                self._upsert_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_FINANCE_BILLING_ACCOUNT,
                    source_id=acct.external_billing_account_id,
                    canonical_entity_id=acct.id,
                )
                stats.mappings_written += 1
                inv_stmt = select(FinanceInvoice).where(
                    FinanceInvoice.tenant_id == tenant_id,
                    FinanceInvoice.billing_account_id == acct.id,
                )
                invoices = list(db.scalars(inv_stmt).all())
                stats.finance_invoices_upserted += len(invoices)
                for inv in invoices:
                    self._upsert_mapping(
                        db=db,
                        tenant_id=tenant_id,
                        source_connection_id=connection.id,
                        entity_type=ENTITY_FINANCE_INVOICE,
                        source_id=inv.external_invoice_id,
                        canonical_entity_id=inv.id,
                    )
                    stats.mappings_written += 1
            stats.warnings.append(
                "Demo finance sync: rows materialised from customer demo profiles, not from Xero Online Invoicing."
            )
            return ConnectorSyncResult(
                ok=True,
                message=f"Synced finance summaries for {stats.finance_billing_accounts_upserted} billing account(s).",
                completed_at=now,
                next_cursor=_iso_now(),
                stats=stats,
            )

        stats.warnings.append(
            "Live Xero API ingestion is not enabled in this release. Enable demo_mode to materialise canonical finance rows."
        )
        return ConnectorSyncResult(
            ok=True,
            message="No finance rows written: awaiting live Xero read path (Phase 0 scope).",
            completed_at=now,
            next_cursor=cursor,
            stats=stats,
        )
