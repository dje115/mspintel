"""Aggregate backup connector facts for workspace views and AI prompts.

Facts are written only by backup-class connector syncs (e.g. Veeam) into ``backup_protection_facts`` — not by AI.
Rollups are tenant-scoped; ``customer_id`` is set only when a source customer external id maps via
``SourceEntityMapping`` for that connection. Do not treat portfolio totals as per-customer SLA proof.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import BackupProtectionFact, Customer, IntegrationSyncRun
from app.services.connectors.constants import BACKUP_CONNECTOR_SYSTEM_TYPES
from app.services.connectors.runtime import ConnectorRuntimeService


class BackupHealthService:
    def __init__(self, db: Session):
        self.db = db

    def _latest_run(self, tenant_id: UUID, connection_id: UUID) -> IntegrationSyncRun | None:
        stmt = (
            select(IntegrationSyncRun)
            .where(
                IntegrationSyncRun.tenant_id == tenant_id,
                IntegrationSyncRun.source_connection_id == connection_id,
            )
            .order_by(IntegrationSyncRun.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def build_workspace(self, tenant_id: UUID) -> dict[str, Any]:
        connections = [
            c
            for c in ConnectorRuntimeService(self.db).list_connections(tenant_id)
            if c.system_type in BACKUP_CONNECTOR_SYSTEM_TYPES
        ]
        facts = list(
            self.db.scalars(select(BackupProtectionFact).where(BackupProtectionFact.tenant_id == tenant_id)).all()
        )
        customers = {c.id: c for c in self.db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()}

        conn_panels: list[dict[str, Any]] = []
        for c in connections:
            run = self._latest_run(tenant_id, c.id)
            fc = Counter()
            for f in facts:
                if f.source_connection_id == c.id:
                    fc[f.fact_kind] += 1
            conn_panels.append(
                {
                    "connection_id": c.id,
                    "display_name": c.display_name,
                    "vendor_system_type": c.system_type,
                    "health_status": c.health_status,
                    "lifecycle_state": c.lifecycle_state,
                    "last_sync_status": run.status if run else None,
                    "last_sync_completed_at": run.completed_at if run else None,
                    "fact_counts": dict(fc),
                }
            )

        by_customer: dict[UUID | None, dict[str, Any]] = {}
        for f in facts:
            key = f.customer_id
            if key not in by_customer:
                by_customer[key] = {
                    "customer_id": key,
                    "customer_name": customers[key].name if key and key in customers else None,
                    "mapped": key is not None,
                    "job_count": 0,
                    "workload_count": 0,
                    "unprotected_workloads": 0,
                    "failed_or_warning_jobs": 0,
                    "signals": [],
                }
            bucket = by_customer[key]
            if f.fact_kind == "backup_job":
                bucket["job_count"] += 1
                st = (f.health_status or "").lower()
                if st in ("failed", "warning"):
                    bucket["failed_or_warning_jobs"] += 1
            elif f.fact_kind == "workload":
                bucket["workload_count"] += 1
                if (f.health_status or "").lower() == "unprotected":
                    bucket["unprotected_workloads"] += 1
            for s in f.signals_json or []:
                if isinstance(s, str) and s not in bucket["signals"]:
                    bucket["signals"].append(s)
                    if len(bucket["signals"]) >= 8:
                        break

        orphan_facts = [f for f in facts if f.customer_id is None and f.source_customer_external_id]
        rollups = []
        for _k, bucket in sorted(by_customer.items(), key=lambda x: (x[0] is None, x[1].get("customer_name") or "")):
            sigs = list(bucket["signals"])[:5]
            rollups.append(
                {
                    "customer_id": bucket["customer_id"],
                    "customer_name": bucket["customer_name"],
                    "mapped": bucket["mapped"],
                    "job_count": bucket["job_count"],
                    "workload_count": bucket["workload_count"],
                    "unprotected_workloads": bucket["unprotected_workloads"],
                    "failed_or_warning_jobs": bucket["failed_or_warning_jobs"],
                    "signals_sample": sigs,
                }
            )

        kind_counts = Counter(f.fact_kind for f in facts)
        unprotected = sum(1 for f in facts if f.fact_kind == "workload" and (f.health_status or "").lower() == "unprotected")
        bad_jobs = sum(
            1
            for f in facts
            if f.fact_kind == "backup_job" and (f.health_status or "").lower() in ("failed", "warning")
        )
        degraded_repos = sum(
            1 for f in facts if f.fact_kind == "repository" and (f.health_status or "").lower() == "degraded"
        )
        overdue_restore = sum(
            1 for f in facts if f.fact_kind == "restore_test" and (f.health_status or "").lower() == "overdue"
        )

        flat_signals: list[str] = []
        for f in facts:
            for s in f.signals_json or []:
                if isinstance(s, str) and s not in flat_signals:
                    flat_signals.append(s)
                if len(flat_signals) >= 16:
                    break
            if len(flat_signals) >= 16:
                break

        samples: list[dict[str, Any]] = []
        for f in facts[:40]:
            samples.append(
                {
                    "vendor": f.vendor_system_type,
                    "kind": f.fact_kind,
                    "display_name": f.display_name,
                    "health_status": f.health_status,
                    "customer_mapped": f.customer_id is not None,
                    "signals": list(f.signals_json or [])[:3],
                    "metrics": dict(f.metrics_json or {}),
                }
            )

        coverage_notes = [
            "Backup facts are vendor-normalised snapshots from your last successful connector sync — not live RPO/RTO guarantees.",
            "Map backup vendor customers to canonical accounts so rollups and AI context line up with Customer 360.",
            "Low incremental change can be healthy (static data) or a signal to verify new systems are under backup scope.",
        ]
        if not connections:
            coverage_notes.insert(0, "No backup-class integration is configured yet (for example Veeam).")
        elif not facts:
            coverage_notes.insert(0, "Backup connection exists but no facts were ingested yet — run a sync from Integrations.")

        summary = {
            "backup_connection_count": len(connections),
            "total_protection_facts": len(facts),
            "facts_by_kind": dict(kind_counts),
            "unprotected_workloads": unprotected,
            "failed_or_warning_jobs": bad_jobs,
            "degraded_repositories": degraded_repos,
            "overdue_restore_tests": overdue_restore,
            "unmapped_fact_rows": len(orphan_facts),
            "deterministic_signals_preview": flat_signals,
        }

        return {
            "summary": summary,
            "coverage_notes": coverage_notes,
            "connections": conn_panels,
            "customer_rollups": rollups,
            "fact_samples": samples,
        }
