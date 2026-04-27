from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer, SourceSystemConnection
from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.capabilities import (
    CAP_LICENCES,
    CAP_MAILBOXES,
    CAP_STORAGE,
    CAP_USERS,
)
from app.services.connectors.constants import CONNECTOR_SYSTEM_MICROSOFT_365, ENTITY_M365_CUSTOMER_POSTURE
from app.services.connectors.manifest import ConnectorConfigField, ConnectorManifest
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult
from app.services.connectors.utils import upsert_source_entity_mapping
from app.services.m365_canonical import upsert_m365_for_customer


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


class Microsoft365ConnectorAdapter(ConnectorAdapter):
    manifest = ConnectorManifest(
        key=CONNECTOR_SYSTEM_MICROSOFT_365,
        display_name="Microsoft 365 / Entra",
        description="Thin v1 M365 hygiene/licensing posture connector for customer intelligence.",
        system_family="productivity",
        maturity="beta",
        auth_modes=("oauth2", "sandbox"),
        capabilities=(CAP_USERS, CAP_LICENCES, CAP_MAILBOXES, CAP_STORAGE),
        sync_modes=("manual", "delta"),
        connector_version="m365_v1",
        default_cadence_minutes=180,
        implemented=True,
        import_scope_modes=("all", "selected_names", "name_prefix", "sample_limit"),
        import_scope_filter_keys=("names", "name_prefix", "sample_limit"),
        config_fields=(
            ConnectorConfigField(key="demo_mode", label="Demo mode", required=False, secret=False),
            ConnectorConfigField(key="tenant_id", label="Tenant ID", required=False, secret=False),
            ConnectorConfigField(key="client_id", label="Client ID", required=False, secret=False),
            ConnectorConfigField(key="client_secret", label="Client Secret", required=False, secret=True),
            ConnectorConfigField(key="include_usage_signals", label="Include usage summary", required=False, secret=False),
            ConnectorConfigField(key="include_entra_summary", label="Include Entra summary", required=False, secret=False),
            ConnectorConfigField(key="include_azure_summary", label="Include Azure summary", required=False, secret=False),
        ),
        ui_help_text=(
            "Supports tenant-scoped M365/Entra posture sync with safe demo-mode fallback. Live Graph depth is intentionally limited."
        ),
    )

    def _is_demo_mode(self, config: dict) -> bool:
        return bool(config.get("demo_mode")) or str(config.get("sandbox") or "").lower() in ("1", "true", "yes")

    def _oauth_fields_present(self, config: dict) -> bool:
        return all(bool(str(config.get(k) or "").strip()) for k in ("tenant_id", "client_id", "client_secret"))

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
                message="Demo mode enabled: sync will use seeded microsoft_365 posture facts (tenant-scoped, deterministic).",
                checked_at=datetime.now(UTC),
                metadata={"mode": "demo_profile"},
            )
        if self._oauth_fields_present(config):
            return ConnectorTestResult(
                ok=True,
                message=(
                    "OAuth app registration fields are present. This phase persists practical posture facts; deeper Graph coverage remains limited."
                ),
                checked_at=datetime.now(UTC),
                metadata={"mode": "credentials_only"},
            )
        return ConnectorTestResult(
            ok=False,
            message="Set demo_mode=true for v1 sync, or provide tenant_id, client_id, and client_secret for future live Graph reads.",
            checked_at=datetime.now(UTC),
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
        if not self._is_demo_mode(config):
            stats.warnings.append(
                "Live Graph ingestion depth is intentionally constrained in this phase; enable demo_mode for deterministic posture sync."
            )
            return ConnectorSyncResult(
                ok=True,
                message="No M365 rows written: waiting for live Graph read extension.",
                completed_at=datetime.now(UTC),
                next_cursor=cursor,
                stats=stats,
            )

        stmt = select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.name)
        customers = list(db.scalars(stmt).all())
        scope_mode = connection.import_scope_mode or "all"
        scope_filters = connection.import_scope_filters or {}
        selected_names = {str(n) for n in (scope_filters.get("names") or [])}
        prefix = str(scope_filters.get("name_prefix") or "").lower()
        sample_limit = int(scope_filters.get("sample_limit") or 0)
        processed = 0
        for customer in customers:
            if scope_mode == "selected_names" and customer.name not in selected_names:
                continue
            if scope_mode == "name_prefix" and prefix and not customer.name.lower().startswith(prefix):
                continue
            if scope_mode == "sample_limit" and sample_limit > 0 and processed >= sample_limit:
                break
            posture = upsert_m365_for_customer(
                db,
                tenant_id=tenant_id,
                customer_id=customer.id,
                demo_profile=customer.demo_profile,
                source_connection_id=connection.id,
                provenance="m365_connector_demo",
            )
            if not posture:
                continue
            processed += 1
            stats.m365_postures_upserted += 1
            upsert_source_entity_mapping(
                db=db,
                tenant_id=tenant_id,
                source_connection_id=connection.id,
                entity_type=ENTITY_M365_CUSTOMER_POSTURE,
                source_id=f"m365-posture:{customer.id}",
                canonical_entity_id=posture.id,
            )
            stats.mappings_written += 1
        stats.warnings.append(
            "Microsoft sync may be demo-backed; treat outputs as directional where live telemetry is absent."
        )
        return ConnectorSyncResult(
            ok=True,
            message=f"Synced M365 postures for {stats.m365_postures_upserted} customer(s).",
            completed_at=datetime.now(UTC),
            next_cursor=_iso_now(),
            stats=stats,
        )

