"""Veeam / VSPC-style backup ingestion (Connector Lab compatible; production API paths evolve per tenant)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import BackupProtectionFact, SourceEntityMapping, SourceSystemConnection
from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.capabilities import CAP_BACKUP_JOBS
from app.services.connectors.constants import CONNECTOR_SYSTEM_VEEAM, ENTITY_CUSTOMER
from app.services.connectors.manifest import ConnectorConfigField, ConnectorManifest
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult


def _parse_dt(val: object) -> datetime | None:
    if val is None:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except ValueError:
        return None


def _job_signals(
    *,
    status: str,
    last_run: datetime | None,
    processed_mb: float | None,
    change_pct: float | None,
) -> list[str]:
    out: list[str] = []
    st = (status or "").lower()
    if st == "failed":
        out.append("Backup job reported failure status — verify alerts, storage, and guest quiescing.")
    elif st == "warning":
        out.append("Backup job is in a warning state — review session logs and retry policy.")
    if last_run is not None:
        if datetime.now(UTC) - last_run.replace(tzinfo=last_run.tzinfo or UTC) > timedelta(hours=48):
            out.append("Last run timestamp is older than 48h — confirm schedule, window, and monitoring.")
    if processed_mb is not None and change_pct is not None and processed_mb >= 500 and change_pct < 1.0:
        out.append(
            "Processed volume is sizeable but incremental change rate is very low — validate scope "
            "(quiet period, static dataset, copy job vs backup, or possible agent coverage gap on new workloads)."
        )
    return out


class VeeamConnectorAdapter(ConnectorAdapter):
    manifest = ConnectorManifest(
        key=CONNECTOR_SYSTEM_VEEAM,
        display_name="Veeam",
        description="Backup job and workload inventory via HTTP API (Connector Lab parity path; extend for live VSPC).",
        system_family="backup",
        maturity="beta",
        auth_modes=("api_key",),
        capabilities=(CAP_BACKUP_JOBS,),
        sync_modes=("manual", "delta"),
        connector_version="v1",
        default_cadence_minutes=120,
        implemented=True,
        import_scope_modes=("all",),
        import_scope_filter_keys=(),
        config_fields=(
            ConnectorConfigField(key="base_url", label="Base URL", required=True, secret=False),
            ConnectorConfigField(key="api_key", label="API key", required=False, secret=True),
            ConnectorConfigField(key="token", label="Bearer token", required=False, secret=True),
        ),
        ui_help_text=(
            "Point base URL at your Veeam management API root (Connector Lab uses `/veeam`). "
            "Use API key or bearer token as required by your deployment."
        ),
    )

    def _headers(self, config: dict) -> dict[str, str]:
        api_key = str(config.get("api_key") or "").strip()
        token = str(config.get("token") or "").strip()
        if api_key:
            return {"X-API-Key": api_key, "Content-Type": "application/json"}
        if token:
            return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        return {"Content-Type": "application/json"}

    def _base_url(self, connection: SourceSystemConnection, config: dict) -> str:
        base_url = (connection.base_url or config.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("Veeam base_url is required")
        return base_url

    def validate_config(self, auth_mode: str, config: dict) -> list[str]:
        base_url = str(config.get("base_url") or "").strip()
        if not base_url:
            return ["base_url"]
        if not (config.get("api_key") or config.get("token")):
            return ["api_key"]
        return []

    def test_connection(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
    ) -> ConnectorTestResult:
        del db, tenant_id
        try:
            base = self._base_url(connection, config)
            headers = self._headers(config)
            with httpx.Client(timeout=30.0) as client:
                r = client.get(f"{base}/customers", params={"page": 1, "page_size": 1}, headers=headers)
            if r.status_code >= 400:
                return ConnectorTestResult(
                    ok=False,
                    message=f"Backup API returned HTTP {r.status_code}. Check URL, token, and vendor path prefix.",
                    checked_at=datetime.now(UTC),
                )
            return ConnectorTestResult(
                ok=True,
                message="Reachable backup directory endpoint (customers).",
                checked_at=datetime.now(UTC),
            )
        except httpx.RequestError as exc:
            return ConnectorTestResult(
                ok=False,
                message=f"Network error reaching backup API: {exc!s}",
                checked_at=datetime.now(UTC),
            )
        except ValueError as exc:
            return ConnectorTestResult(ok=False, message=str(exc), checked_at=datetime.now(UTC))

    def _fetch_all(self, client: httpx.Client, base: str, path: str, headers: dict[str, str]) -> list[dict]:
        page = 1
        items: list[dict] = []
        while True:
            r = client.get(f"{base}{path}", params={"page": page, "page_size": 200}, headers=headers)
            r.raise_for_status()
            payload = r.json()
            batch = list(payload.get("items") or [])
            items.extend(batch)
            if not payload.get("has_more"):
                break
            page += 1
        return items

    def _canonical_customer_id(self, db: Session, tenant_id: UUID, connection_id: UUID, source_customer_id: str | None):
        if not source_customer_id:
            return None
        m = db.scalars(
            select(SourceEntityMapping).where(
                SourceEntityMapping.tenant_id == tenant_id,
                SourceEntityMapping.source_connection_id == connection_id,
                SourceEntityMapping.entity_type == ENTITY_CUSTOMER,
                SourceEntityMapping.source_id == str(source_customer_id),
            )
        ).first()
        return m.canonical_entity_id if m else None

    def run_sync(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
        cursor: str | None,
    ) -> ConnectorSyncResult:
        del cursor
        stats = ConnectorSyncStats()
        now = datetime.now(UTC)
        try:
            base = self._base_url(connection, config)
            headers = self._headers(config)
            with httpx.Client(timeout=120.0) as client:
                jobs = self._fetch_all(client, base, "/backup-jobs", headers)
                workloads = self._fetch_all(client, base, "/workloads", headers)
                repos = self._fetch_all(client, base, "/repositories", headers)
                restores = self._fetch_all(client, base, "/restore-tests", headers)

            db.execute(
                delete(BackupProtectionFact).where(
                    BackupProtectionFact.tenant_id == tenant_id,
                    BackupProtectionFact.source_connection_id == connection.id,
                )
            )

            for row in jobs:
                jid = str(row.get("id") or "")
                if not jid:
                    continue
                cust_ext = str(row.get("customer_id") or "") or None
                last_run = _parse_dt(row.get("last_run_at"))
                proc_mb = row.get("processed_mb")
                chg_mb = row.get("transfer_change_mb")
                chg_pct = row.get("change_pct")
                try:
                    proc_mb_f = float(proc_mb) if proc_mb is not None else None
                except (TypeError, ValueError):
                    proc_mb_f = None
                try:
                    chg_pct_f = float(chg_pct) if chg_pct is not None else None
                except (TypeError, ValueError):
                    chg_pct_f = None
                status = str(row.get("status") or "")
                sigs = _job_signals(
                    status=status,
                    last_run=last_run,
                    processed_mb=proc_mb_f,
                    change_pct=chg_pct_f,
                )
                metrics = {}
                if proc_mb_f is not None:
                    metrics["processed_mb"] = proc_mb_f
                if chg_mb is not None:
                    try:
                        metrics["transfer_change_mb"] = float(chg_mb)
                    except (TypeError, ValueError):
                        pass
                if chg_pct_f is not None:
                    metrics["change_pct"] = chg_pct_f

                db.add(
                    BackupProtectionFact(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        source_connection_id=connection.id,
                        vendor_system_type=CONNECTOR_SYSTEM_VEEAM,
                        fact_kind="backup_job",
                        source_external_id=jid,
                        source_customer_external_id=cust_ext,
                        customer_id=self._canonical_customer_id(db, tenant_id, connection.id, cust_ext),
                        display_name=f"Job {jid}",
                        health_status=status or None,
                        observed_at=last_run,
                        metrics_json=metrics or None,
                        signals_json=sigs or None,
                    )
                )
                stats.backup_facts_upserted += 1

            for row in workloads:
                wid = str(row.get("id") or "")
                if not wid:
                    continue
                cust_ext = str(row.get("customer_id") or "") or None
                protected = row.get("protected")
                wl_name = str(row.get("workload") or wid)
                unprotected = protected is False
                sigs: list[str] = []
                if unprotected:
                    sigs.append(
                        "Workload marked as not protected — possible new server or guest without backup agent/policy."
                    )
                db.add(
                    BackupProtectionFact(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        source_connection_id=connection.id,
                        vendor_system_type=CONNECTOR_SYSTEM_VEEAM,
                        fact_kind="workload",
                        source_external_id=wid,
                        source_customer_external_id=cust_ext,
                        customer_id=self._canonical_customer_id(db, tenant_id, connection.id, cust_ext),
                        display_name=wl_name,
                        health_status="unprotected" if unprotected else "protected",
                        observed_at=_parse_dt(row.get("updated_at")),
                        metrics_json={"protected": bool(protected)} if protected is not None else None,
                        signals_json=sigs or None,
                    )
                )
                stats.backup_facts_upserted += 1

            for row in repos:
                rid = str(row.get("id") or "")
                if not rid:
                    continue
                health = str(row.get("health") or "")
                sigs = []
                if health == "degraded":
                    sigs.append("Repository health reported as degraded — capacity, retention, or hardware follow-up.")
                db.add(
                    BackupProtectionFact(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        source_connection_id=connection.id,
                        vendor_system_type=CONNECTOR_SYSTEM_VEEAM,
                        fact_kind="repository",
                        source_external_id=rid,
                        source_customer_external_id=None,
                        customer_id=None,
                        display_name=str(row.get("name") or rid),
                        health_status=health or None,
                        observed_at=_parse_dt(row.get("updated_at")),
                        metrics_json=None,
                        signals_json=sigs or None,
                    )
                )
                stats.backup_facts_upserted += 1

            for row in restores:
                tid = str(row.get("id") or "")
                if not tid:
                    continue
                cust_ext = str(row.get("customer_id") or "") or None
                st = str(row.get("status") or "")
                sigs = []
                if st == "overdue":
                    sigs.append("Restore test overdue — validate DR rehearsal cadence with the customer.")
                db.add(
                    BackupProtectionFact(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        source_connection_id=connection.id,
                        vendor_system_type=CONNECTOR_SYSTEM_VEEAM,
                        fact_kind="restore_test",
                        source_external_id=tid,
                        source_customer_external_id=cust_ext,
                        customer_id=self._canonical_customer_id(db, tenant_id, connection.id, cust_ext),
                        display_name="Restore test",
                        health_status=st or None,
                        observed_at=_parse_dt(row.get("last_tested_at")),
                        metrics_json=None,
                        signals_json=sigs or None,
                    )
                )
                stats.backup_facts_upserted += 1

            return ConnectorSyncResult(
                ok=True,
                message=f"Ingested {stats.backup_facts_upserted} backup fact rows.",
                completed_at=now,
                next_cursor=None,
                stats=stats,
            )
        except httpx.HTTPStatusError as exc:
            stats.warnings.append(f"HTTP {exc.response.status_code} from backup API.")
            return ConnectorSyncResult(
                ok=False,
                message=f"Backup API error: HTTP {exc.response.status_code}",
                completed_at=now,
                next_cursor=None,
                stats=stats,
            )
        except httpx.RequestError as exc:
            return ConnectorSyncResult(
                ok=False,
                message=f"Network error during backup sync: {exc!s}",
                completed_at=now,
                next_cursor=None,
                stats=stats,
            )
        except Exception as exc:  # noqa: BLE001
            return ConnectorSyncResult(
                ok=False,
                message=f"Backup sync failed: {exc!s}",
                completed_at=now,
                next_cursor=None,
                stats=stats,
            )
