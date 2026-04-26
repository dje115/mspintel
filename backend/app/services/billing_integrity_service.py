"""Tenant-level billing integrity / revenue assurance summaries (honest, coverage-aware)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer, FinanceBillingAccount, FinanceBillingSnapshot


@dataclass
class AccountIntegrityRow:
    customer_id: UUID
    customer_name: str
    finance_linked: bool
    billed_mailboxes: int | None
    service_mailboxes: int | None
    billed_users: int | None
    service_licensed_users: int | None
    payment_friction: str | None
    aged_outstanding_cents: int | None
    confidence_level: str | None
    signals: list[str]


class BillingIntegrityService:
    def __init__(self, db: Session):
        self.db = db

    def _latest_snapshot(self, tenant_id: UUID, billing_account_id: UUID) -> FinanceBillingSnapshot | None:
        stmt = (
            select(FinanceBillingSnapshot)
            .where(
                FinanceBillingSnapshot.tenant_id == tenant_id,
                FinanceBillingSnapshot.billing_account_id == billing_account_id,
            )
            .order_by(FinanceBillingSnapshot.effective_date.desc(), FinanceBillingSnapshot.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def build_workspace(self, tenant_id: UUID) -> dict[str, Any]:
        cust_stmt = select(Customer).where(Customer.tenant_id == tenant_id)
        customers = list(self.db.scalars(cust_stmt).all())
        acct_stmt = select(FinanceBillingAccount).where(FinanceBillingAccount.tenant_id == tenant_id)
        accounts = list(self.db.scalars(acct_stmt).all())
        acct_by_customer = {a.customer_id: a for a in accounts if a.customer_id}

        latest_snaps: dict[UUID, FinanceBillingSnapshot] = {}
        for a in accounts:
            snap = self._latest_snapshot(tenant_id, a.id)
            if snap:
                latest_snaps[a.id] = snap

        rows: list[AccountIntegrityRow] = []
        underbilling: list[UUID] = []
        overbilling_risk: list[UUID] = []
        payment_friction: list[UUID] = []

        for c in customers:
            acct = acct_by_customer.get(c.id)
            snap = latest_snaps.get(acct.id) if acct else None
            signals: list[str] = []
            bm, sm = None, None
            bu, su = None, None
            pay = None
            aged = None
            conf = None
            if snap:
                bm = snap.billed_mailboxes
                sm = snap.service_active_mailboxes
                bu = snap.billed_users
                su = snap.service_licensed_users
                pay = snap.payment_status_summary
                aged = snap.aged_outstanding_cents
                conf = snap.confidence_level
                if bm is not None and sm is not None and sm > bm + 1:
                    signals.append("Measured mailboxes exceed billed seats — possible underbilling.")
                    underbilling.append(c.id)
                if bm is not None and sm is not None and bm > sm + 5:
                    signals.append("Billed mailboxes materially above measured active mailboxes — verify entitlements.")
                    overbilling_risk.append(c.id)
                if pay and pay not in ("none", "unknown"):
                    signals.append(f"Payment / invoice friction flag: {pay}.")
                    if pay != "none":
                        payment_friction.append(c.id)
                if aged and aged > 0:
                    signals.append("Aged outstanding balance recorded on latest snapshot.")
            elif c.demo_profile and (c.demo_profile.get("billing") or {}).get("billed_m365_seats") is not None:
                signals.append("Billing hints exist only in legacy demo_profile JSON — link accounting for canonical finance.")
            else:
                signals.append("No finance linkage or billing snapshot — commercial signals are incomplete.")

            rows.append(
                AccountIntegrityRow(
                    customer_id=c.id,
                    customer_name=c.name,
                    finance_linked=bool(acct),
                    billed_mailboxes=bm,
                    service_mailboxes=sm,
                    billed_users=bu,
                    service_licensed_users=su,
                    payment_friction=pay,
                    aged_outstanding_cents=aged,
                    confidence_level=conf,
                    signals=signals,
                )
            )

        linked = sum(1 for r in rows if r.finance_linked)
        missing = len(rows) - linked
        orphan_accounts = [a for a in accounts if a.customer_id is None]

        return {
            "summary": {
                "customer_count": len(customers),
                "finance_linked_count": linked,
                "missing_finance_link_count": missing,
                "orphan_billing_account_count": len(orphan_accounts),
                "underbilling_candidate_count": len(set(underbilling)),
                "overbilling_risk_count": len(set(overbilling_risk)),
                "payment_friction_count": len(set(payment_friction)),
            },
            "coverage_notes": [
                "Figures are only as complete as synced accounting + service telemetry allow.",
                "Finance Phase 0 uses canonical tables seeded from demo profiles or Xero demo_mode sync — not a full ledger.",
            ],
            "accounts": [asdict(r) for r in rows],
        }

    def customer_finance_panel(self, tenant_id: UUID, customer_id: UUID) -> dict[str, Any]:
        """Structured finance slice for Customer 360 (canonical-first, honest about gaps)."""
        cust = self.db.get(Customer, customer_id)
        if not cust or cust.tenant_id != tenant_id:
            return {"error": "not_found"}
        stmt = select(FinanceBillingAccount).where(
            FinanceBillingAccount.tenant_id == tenant_id,
            FinanceBillingAccount.customer_id == customer_id,
        )
        acct = self.db.scalars(stmt).first()
        notes: list[str] = []
        highlights: list[str] = []
        if not acct:
            notes.append("No canonical finance billing account linked — confidence for commercial math is low.")
            if cust.demo_profile and (cust.demo_profile.get("billing") or {}):
                notes.append("Legacy demo_profile billing hints exist but are not treated as ledger truth.")
            return {
                "finance_linked": False,
                "billing_account_id": None,
                "display_name": None,
                "currency_code": None,
                "snapshot_effective_date": None,
                "billed_mailboxes": None,
                "service_active_mailboxes": None,
                "billed_users": None,
                "service_licensed_users": None,
                "payment_status_summary": None,
                "aged_outstanding_cents": None,
                "confidence_level": "low",
                "integrity_highlights": highlights,
                "confidence_notes": notes,
                "next_commercial_action_placeholder": (
                    "Link accounting (Xero demo_mode or future live connector) before revenue assurance conclusions."
                ),
                "provenance": {"canonical": False},
            }

        snap = self._latest_snapshot(tenant_id, acct.id)
        if snap:
            if snap.billed_mailboxes is not None and snap.service_active_mailboxes is not None:
                if snap.service_active_mailboxes > snap.billed_mailboxes + 1:
                    highlights.append("Mailbox footprint exceeds billed seats on latest snapshot.")
                if snap.billed_mailboxes > snap.service_active_mailboxes + 5:
                    highlights.append("Billed mailboxes exceed measured active mailboxes — validate SKUs.")
            if snap.aged_outstanding_cents and snap.aged_outstanding_cents > 0:
                highlights.append("Outstanding balance on latest finance snapshot — align with collections.")
            if snap.payment_status_summary and snap.payment_status_summary not in ("none", "unknown"):
                highlights.append(f"Invoice friction flag: {snap.payment_status_summary}.")
        else:
            notes.append("Billing account exists but no snapshot row yet — run finance sync or reseed.")

        if (acct.extra or {}).get("provenance") == "demo_seed":
            notes.append("Data materialised from synthetic demo seed, not a live accounting export.")

        return {
            "finance_linked": True,
            "billing_account_id": acct.id,
            "display_name": acct.display_name,
            "currency_code": acct.currency_code,
            "snapshot_effective_date": snap.effective_date.isoformat() if snap else None,
            "billed_mailboxes": snap.billed_mailboxes if snap else None,
            "service_active_mailboxes": snap.service_active_mailboxes if snap else None,
            "billed_users": snap.billed_users if snap else None,
            "service_licensed_users": snap.service_licensed_users if snap else None,
            "payment_status_summary": snap.payment_status_summary if snap else None,
            "aged_outstanding_cents": snap.aged_outstanding_cents if snap else None,
            "confidence_level": snap.confidence_level if snap else "medium",
            "integrity_highlights": highlights,
            "confidence_notes": notes,
            "next_commercial_action_placeholder": (
                "Validate billed quantities vs entitlements; schedule finance + service alignment review."
            ),
            "provenance": {"canonical": True, "extra": acct.extra},
        }
