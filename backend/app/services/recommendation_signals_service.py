"""Derive open recommendations from connector-backed workspace signals (idempotent per run).

Open rows prefixed with ``[Auto] …`` are owned by this sync: summaries update, and rows complete when the
underlying signal clears. Manual recommendations must not reuse those prefixes. All operations are tenant-scoped.
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Quote, Recommendation, Ticket
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.connectors.runtime import ConnectorRuntimeService
from app.services.m365_health_service import M365HealthService

# Stable prefixes — used to upsert/retire auto-generated rows without a DB migration.
PREFIX_MAPPING = "[Auto] mapping-backlog:"
PREFIX_OVERDUE = "[Auto] overdue-invoices:"
PREFIX_TICKETS = "[Auto] open-ticket-pressure:"
PREFIX_LOST_QUOTE = "[Auto] lost-quote-revisit:"
PREFIX_M365 = "[Auto] m365-hygiene:"

OPEN_TICKET_THRESHOLD = 4
M365_INACTIVE_THRESHOLD = 5
M365_UNUSED_LIC_THRESHOLD = 3


def _clip(s: str, max_len: int = 280) -> str:
    return s[:max_len]


class RecommendationSignalsService:
    def __init__(self, db: Session):
        self.db = db

    def _first_open_auto(
        self, tenant_id: UUID, prefix: str, customer_id: UUID | None
    ) -> Recommendation | None:
        stmt = select(Recommendation).where(
            Recommendation.tenant_id == tenant_id,
            Recommendation.status == "open",
            Recommendation.summary.like(prefix + "%"),
        )
        if customer_id is not None:
            stmt = stmt.where(Recommendation.customer_id == customer_id)
        else:
            stmt = stmt.where(Recommendation.customer_id.is_(None))
        return self.db.scalars(stmt.order_by(Recommendation.created_at.desc())).first()

    def _retire_open_auto_customer_scope(
        self, tenant_id: UUID, prefix: str, keep: set[UUID]
    ) -> int:
        stmt = select(Recommendation).where(
            Recommendation.tenant_id == tenant_id,
            Recommendation.status == "open",
            Recommendation.summary.like(prefix + "%"),
            Recommendation.customer_id.isnot(None),
        )
        n = 0
        for rec in self.db.scalars(stmt).all():
            cid = rec.customer_id
            if cid and cid not in keep:
                rec.status = "completed"
                n += 1
        return n

    def _upsert(
        self,
        tenant_id: UUID,
        scope: str,
        customer_id: UUID | None,
        prefix: str,
        body: str,
        stats: dict[str, int],
    ) -> None:
        summary = _clip(f"{prefix} {body}")
        rec = self._first_open_auto(tenant_id, prefix, customer_id)
        if rec is None:
            self.db.add(
                Recommendation(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    customer_id=customer_id,
                    scope=scope,
                    status="open",
                    summary=summary,
                )
            )
            stats["created"] += 1
        elif rec.summary != summary:
            rec.summary = summary
            stats["updated"] += 1

    def _complete_open_auto(self, tenant_id: UUID, prefix: str, customer_id: UUID | None) -> int:
        stmt = select(Recommendation).where(
            Recommendation.tenant_id == tenant_id,
            Recommendation.status == "open",
            Recommendation.summary.like(prefix + "%"),
        )
        if customer_id is not None:
            stmt = stmt.where(Recommendation.customer_id == customer_id)
        else:
            stmt = stmt.where(Recommendation.customer_id.is_(None))
        n = 0
        for rec in self.db.scalars(stmt).all():
            rec.status = "completed"
            n += 1
        return n

    def sync(self, tenant_id: UUID) -> dict[str, int]:
        stats = {"created": 0, "updated": 0, "completed": 0}

        cov = ConnectorRuntimeService(self.db).coverage_summary(tenant_id)
        pending = int(cov.get("unresolved_mappings") or 0)
        if pending > 0:
            self._upsert(
                tenant_id,
                "service",
                None,
                PREFIX_MAPPING,
                f"{pending} pending mapping review row(s) — resolve under Integrations → Mapping review.",
                stats,
            )
        else:
            stats["completed"] += self._complete_open_auto(tenant_id, PREFIX_MAPPING, None)

        billing_ws: dict[str, Any] = BillingIntegrityService(self.db).build_workspace(tenant_id)
        accounts = list(billing_ws.get("accounts") or [])
        overdue_customers: dict[UUID, int] = {}
        for row in accounts:
            cid = row.get("customer_id")
            oc = int(row.get("overdue_invoice_count") or 0)
            if cid and oc > 0:
                overdue_customers[UUID(str(cid))] = oc

        stats["completed"] += self._retire_open_auto_customer_scope(
            tenant_id, PREFIX_OVERDUE, set(overdue_customers.keys())
        )
        for cid, oc in overdue_customers.items():
            self._upsert(
                tenant_id,
                "service",
                cid,
                PREFIX_OVERDUE,
                f"{oc} overdue invoice(s) — align billing cadence with the account owner.",
                stats,
            )

        ticket_stmt = (
            select(Ticket.customer_id, func.count(Ticket.id))
            .where(Ticket.tenant_id == tenant_id, Ticket.status == "open")
            .group_by(Ticket.customer_id)
            .having(func.count(Ticket.id) >= OPEN_TICKET_THRESHOLD)
        )
        ticket_counts: dict[UUID, int] = {
            row[0]: int(row[1]) for row in self.db.execute(ticket_stmt).all() if row[0]
        }
        stats["completed"] += self._retire_open_auto_customer_scope(
            tenant_id, PREFIX_TICKETS, set(ticket_counts.keys())
        )
        for cid, cnt in ticket_counts.items():
            self._upsert(
                tenant_id,
                "service",
                cid,
                PREFIX_TICKETS,
                f"{cnt} open ticket(s) — review workload and customer expectations.",
                stats,
            )

        lost_stmt = select(Quote.customer_id).where(
            Quote.tenant_id == tenant_id, Quote.status == "lost"
        )
        lost_customers = {row[0] for row in self.db.execute(lost_stmt).all() if row[0]}
        stats["completed"] += self._retire_open_auto_customer_scope(
            tenant_id, PREFIX_LOST_QUOTE, lost_customers
        )
        for cid in lost_customers:
            self._upsert(
                tenant_id,
                "sales",
                cid,
                PREFIX_LOST_QUOTE,
                "Lost quote on file — schedule commercial follow-up or update stage in PSA.",
                stats,
            )

        m365_ws = M365HealthService(self.db).build_workspace(tenant_id)
        m365_need: dict[UUID, str] = {}
        for row in m365_ws.get("customers") or []:
            cid_raw = row.get("customer_id")
            if not cid_raw:
                continue
            cid = UUID(str(cid_raw))
            inactive = int(row.get("inactive_users_30d") or 0)
            unused = int(row.get("unused_licences") or 0)
            licensed = row.get("licensed_users")
            if licensed is None:
                continue
            parts: list[str] = []
            if inactive >= M365_INACTIVE_THRESHOLD:
                parts.append(f"{inactive} inactive users (30d)")
            if unused >= M365_UNUSED_LIC_THRESHOLD:
                parts.append(f"{unused} unused licences")
            if parts:
                m365_need[cid] = " and ".join(parts) + " — review hygiene and licence alignment."

        stats["completed"] += self._retire_open_auto_customer_scope(
            tenant_id, PREFIX_M365, set(m365_need.keys())
        )
        for cid, detail in m365_need.items():
            self._upsert(tenant_id, "executive", cid, PREFIX_M365, detail, stats)

        return stats
