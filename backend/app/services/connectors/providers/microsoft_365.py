from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from uuid import UUID

import httpx
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
from app.services.connectors.constants import (
    CONNECTOR_SYSTEM_MICROSOFT_365,
    ENTITY_CUSTOMER,
    ENTITY_M365_CUSTOMER_POSTURE,
)
from app.services.connectors.manifest import ConnectorConfigField, ConnectorManifest
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult
from app.services.connectors.utils import upsert_source_entity_mapping
from app.services.m365_canonical import upsert_m365_for_customer, upsert_m365_for_customer_payload


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
            "Supports tenant-scoped M365/Entra posture sync with safe demo-mode fallback. Live Graph depth is "
            "intentionally limited; planned scopes include Organization.Read.All, User.Read.All, Reports.Read.All, and Directory.Read.All."
        ),
    )

    def _is_demo_mode(self, config: dict) -> bool:
        return bool(config.get("demo_mode")) or str(config.get("sandbox") or "").lower() in ("1", "true", "yes")

    def _oauth_fields_present(self, config: dict) -> bool:
        return all(bool(str(config.get(k) or "").strip()) for k in ("tenant_id", "client_id", "client_secret"))

    def _connector_lab_base_url(self, connection: SourceSystemConnection, config: dict) -> str:
        configured = str(
            connection.base_url
            or config.get("base_url")
            or os.getenv("M365_BASE_URL")
            or os.getenv("CONNECTOR_LAB_BASE_URL")
            or ""
        ).strip()
        if not configured:
            return ""
        configured = configured.rstrip("/")
        if configured.endswith("/m365"):
            return configured
        return f"{configured}/m365"

    @staticmethod
    def _connector_lab_headers(config: dict) -> dict[str, str]:
        token = str(config.get("token") or os.getenv("CONNECTOR_LAB_TOKEN") or "").strip()
        api_key = str(config.get("api_key") or os.getenv("CONNECTOR_LAB_API_KEY") or "").strip()
        if api_key:
            return {"X-API-Key": api_key, "Content-Type": "application/json"}
        if token:
            return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        return {"Content-Type": "application/json"}

    def _fetch_resource(
        self,
        *,
        base_url: str,
        path: str,
        config: dict,
        page_size: int = 200,
    ) -> list[dict]:
        rows: list[dict] = []
        page = 1
        with httpx.Client(timeout=20.0) as client:
            while True:
                resp = client.get(
                    f"{base_url}/{path.lstrip('/')}",
                    headers=self._connector_lab_headers(config),
                    params={"page": page, "page_size": page_size},
                )
                if resp.status_code == 401:
                    raise ValueError("M365 connector auth rejected by Connector Lab.")
                if resp.status_code >= 400:
                    raise ValueError(f"M365 connector lab request failed for /{path}: HTTP {resp.status_code}.")
                payload = resp.json() if resp.content else {}
                if not isinstance(payload, dict):
                    raise ValueError(f"M365 connector returned unexpected payload for /{path}.")
                items = payload.get("items")
                if not isinstance(items, list):
                    raise ValueError(f"M365 connector payload missing items list for /{path}.")
                rows.extend([dict(r) for r in items if isinstance(r, dict)])
                if not bool(payload.get("has_more")):
                    break
                page += 1
        return rows

    @staticmethod
    def _confidence_from_hygiene(hygiene_count: int) -> str:
        if hygiene_count >= 2:
            return "high"
        if hygiene_count == 1:
            return "medium"
        return "low"

    @staticmethod
    def _norm_customer_label(value: str) -> str:
        v = re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()
        for suffix in (" limited", " ltd", " llp", " plc", " group", " holdings", " services"):
            if v.endswith(suffix):
                v = v[: -len(suffix)].strip()
        return v

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
        base_url = self._connector_lab_base_url(connection, config)
        if base_url:
            try:
                tenants = self._fetch_resource(base_url=base_url, path="tenants", config=config, page_size=20)
            except ValueError as exc:
                return ConnectorTestResult(ok=False, message=str(exc), checked_at=datetime.now(UTC))
            if not tenants:
                return ConnectorTestResult(
                    ok=False,
                    message="M365 namespace reachable but no tenant rows were returned.",
                    checked_at=datetime.now(UTC),
                    metadata={"mode": "connector_lab"},
                )
            return ConnectorTestResult(
                ok=True,
                message="Connector Lab M365 namespace is reachable and returned tenant records.",
                checked_at=datetime.now(UTC),
                metadata={"mode": "connector_lab", "tenant_rows": len(tenants), "base_url": base_url},
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
        if self._is_demo_mode(config):
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

        base_url = self._connector_lab_base_url(connection, config)
        if base_url:
            try:
                tenants = self._fetch_resource(base_url=base_url, path="tenants", config=config)
                licence_rows = self._fetch_resource(base_url=base_url, path="licence-summary", config=config)
                mailbox_rows = self._fetch_resource(base_url=base_url, path="mailbox-counts", config=config)
                hygiene_rows = self._fetch_resource(base_url=base_url, path="hygiene-findings", config=config)
            except ValueError as exc:
                return ConnectorSyncResult(
                    ok=False,
                    message=str(exc),
                    completed_at=datetime.now(UTC),
                    next_cursor=cursor,
                    stats=stats,
                )

            tenant_rows_by_id = {str(r.get("tenant_id") or ""): r for r in licence_rows}
            mailbox_rows_by_id = {str(r.get("tenant_id") or ""): r for r in mailbox_rows}
            hygiene_by_tenant: dict[str, list[dict]] = {}
            for row in hygiene_rows:
                tid = str(row.get("tenant_id") or "")
                hygiene_by_tenant.setdefault(tid, []).append(row)

            stmt = select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.name)
            customers = list(db.scalars(stmt).all())
            customer_by_name = {self._norm_customer_label(c.name): c for c in customers}
            for tenant_row in tenants:
                tenant_ref = str(tenant_row.get("id") or "").strip()
                if not tenant_ref:
                    continue
                hint = self._norm_customer_label(str(tenant_row.get("customer_hint") or ""))
                customer = customer_by_name.get(hint)
                if not customer:
                    fallback_name = str(tenant_row.get("customer_hint") or tenant_row.get("tenant_name") or "").strip()
                    if fallback_name:
                        customer = Customer(
                            tenant_id=tenant_id,
                            name=fallback_name[:180],
                            status="watch",
                            owner_name=None,
                            external_ref=f"m365:{tenant_ref}",
                        )
                        db.add(customer)
                        db.flush()
                        upsert_source_entity_mapping(
                            db=db,
                            tenant_id=tenant_id,
                            source_connection_id=connection.id,
                            entity_type=ENTITY_CUSTOMER,
                            source_id=f"m365-customer:{tenant_ref}",
                            canonical_entity_id=customer.id,
                        )
                        stats.mappings_written += 1
                        stats.warnings.append(
                            f"Created canonical customer '{fallback_name}' from M365 tenant hint (unmatched to existing customer)."
                        )
                    else:
                        continue
                licence = tenant_rows_by_id.get(tenant_ref, {})
                mailbox = mailbox_rows_by_id.get(tenant_ref, {})
                findings = hygiene_by_tenant.get(tenant_ref, [])
                row_payload = {
                    "tenant_ref": tenant_ref,
                    "tenant_name": tenant_row.get("tenant_name"),
                    "tenant_domains": [tenant_row.get("tenant_name")] if tenant_row.get("tenant_name") else [],
                    "licensed_users": licence.get("licensed_users"),
                    "active_users_30d": licence.get("active_users_30d"),
                    "inactive_users_30d": licence.get("inactive_users_30d"),
                    "mailboxes": mailbox.get("mailboxes"),
                    "shared_mailboxes": mailbox.get("shared_mailboxes"),
                    "hygiene_findings": [str(f.get("finding")) for f in findings if f.get("finding")],
                    "coverage_notes": [
                        "Materialised from Connector Lab M365 endpoints; treat as mock vendor telemetry.",
                    ],
                    "confidence_level": self._confidence_from_hygiene(len(findings)),
                }
                posture = upsert_m365_for_customer_payload(
                    db,
                    tenant_id=tenant_id,
                    customer_id=customer.id,
                    source_connection_id=connection.id,
                    payload=row_payload,
                    provenance="m365_connector_lab",
                )
                stats.m365_postures_upserted += 1
                upsert_source_entity_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_M365_CUSTOMER_POSTURE,
                    source_id=f"m365-posture:{tenant_ref}",
                    canonical_entity_id=posture.id,
                )
                stats.mappings_written += 1
            if stats.m365_postures_upserted == 0:
                stats.warnings.append("No customer hints in Connector Lab tenants matched canonical customer names.")
            return ConnectorSyncResult(
                ok=True,
                message=f"Synced M365 postures from Connector Lab for {stats.m365_postures_upserted} customer(s).",
                completed_at=datetime.now(UTC),
                next_cursor=_iso_now(),
                stats=stats,
            )

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

        return ConnectorSyncResult(
            ok=True,
            message="No M365 rows written: waiting for live Graph read extension.",
            completed_at=datetime.now(UTC),
            next_cursor=cursor,
            stats=stats,
        )

