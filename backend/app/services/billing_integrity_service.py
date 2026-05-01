"""Tenant-level billing integrity / revenue assurance summaries (honest, coverage-aware)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    Customer,
    FinanceBillingAccount,
    FinanceBillingSnapshot,
    FinanceInvoice,
    FinanceInvoiceLine,
    IntegrationSyncRun,
    M365CustomerPosture,
    SourceSystemConnection,
)


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
    unpaid_invoice_count: int
    overdue_invoice_count: int
    total_amount_due_cents: int
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

    def _invoice_totals_for_account(self, tenant_id: UUID, billing_account_id: UUID) -> dict[str, int | str | None]:
        today = date.today()
        row = self.db.execute(
            select(
                func.count(FinanceInvoice.id),
                func.sum(
                    case(
                        (func.coalesce(FinanceInvoice.outstanding_cents, 0) > 0, 1),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            (func.coalesce(FinanceInvoice.outstanding_cents, 0) > 0)
                            & (FinanceInvoice.due_date.isnot(None))
                            & (FinanceInvoice.due_date < today),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(func.coalesce(FinanceInvoice.outstanding_cents, 0)),
                func.max(FinanceInvoice.issue_date),
            ).where(FinanceInvoice.tenant_id == tenant_id, FinanceInvoice.billing_account_id == billing_account_id)
        ).first()
        return {
            "total": int(row[0] or 0),
            "unpaid": int(row[1] or 0),
            "overdue": int(row[2] or 0),
            "amount_due_cents": int(row[3] or 0),
            "last_invoice_date": row[4].isoformat() if row[4] else None,
        }

    def build_workspace(self, tenant_id: UUID) -> dict[str, Any]:
        cust_stmt = select(Customer).where(Customer.tenant_id == tenant_id)
        customers = list(self.db.scalars(cust_stmt).all())
        acct_stmt = select(FinanceBillingAccount).where(FinanceBillingAccount.tenant_id == tenant_id)
        accounts = list(self.db.scalars(acct_stmt).all())
        acct_by_customer = {a.customer_id: a for a in accounts if a.customer_id}

        latest_snaps: dict[UUID, FinanceBillingSnapshot] = {}
        invoice_rollups: dict[UUID, dict[str, int | str | None]] = {}
        for a in accounts:
            snap = self._latest_snapshot(tenant_id, a.id)
            if snap:
                latest_snaps[a.id] = snap
            invoice_rollups[a.id] = self._invoice_totals_for_account(tenant_id, a.id)

        rows: list[AccountIntegrityRow] = []
        underbilling: list[UUID] = []
        overbilling_risk: list[UUID] = []
        payment_friction: list[UUID] = []

        for c in customers:
            acct = acct_by_customer.get(c.id)
            snap = latest_snaps.get(acct.id) if acct else None
            inv = invoice_rollups.get(acct.id, {"unpaid": 0, "overdue": 0, "amount_due_cents": 0}) if acct else {
                "unpaid": 0,
                "overdue": 0,
                "amount_due_cents": 0,
            }
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
            if int(inv["overdue"] or 0) > 0:
                signals.append(f"{int(inv['overdue'])} overdue invoice(s) need billing/admin review.")
                payment_friction.append(c.id)
            if int(inv["amount_due_cents"] or 0) > 0 and not signals:
                signals.append("Outstanding invoices detected; align finance and account cadence.")

            m365 = self.db.scalars(
                select(M365CustomerPosture).where(
                    M365CustomerPosture.tenant_id == tenant_id,
                    M365CustomerPosture.customer_id == c.id,
                )
            ).first()
            if m365:
                if bu is not None and m365.active_users_30d is not None and m365.active_users_30d > bu + 2:
                    signals.append("M365 active users exceed billed users — possible M365 underbilling opportunity.")
                    underbilling.append(c.id)
                if bm is not None and m365.mailbox_count is not None and m365.mailbox_count > bm + 2:
                    signals.append("M365 mailbox count exceeds billed mailboxes — verify Microsoft SKU alignment.")
                    underbilling.append(c.id)
                if (m365.unused_licences or 0) >= 5:
                    signals.append("Unused Microsoft licences indicate optimisation headroom.")
                if (m365.stale_users_90d or 0) >= 10:
                    signals.append("High stale M365 identity count — check for over-licensed dormant users.")
                if (m365.disabled_users or 0) >= 5:
                    signals.append("Disabled M365 identities present — validate billing and hygiene assumptions.")
                if m365.confidence_level == "low":
                    signals.append("M365 confidence is low; treat licence and usage deltas as directional only.")
            else:
                signals.append("No M365 service context linked yet — service/contract variance checks remain partial.")

            if not acct:
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
                    unpaid_invoice_count=int(inv["unpaid"] or 0),
                    overdue_invoice_count=int(inv["overdue"] or 0),
                    total_amount_due_cents=int(inv["amount_due_cents"] or 0),
                    confidence_level=conf,
                    signals=signals,
                )
            )

        linked = sum(1 for r in rows if r.finance_linked)
        missing = len(rows) - linked
        orphan_accounts = [a for a in accounts if a.customer_id is None]
        unlinked_finance_contact_count = len(orphan_accounts)
        total_invoice_count = sum(int(invoice_rollups.get(a.id, {}).get("total") or 0) for a in accounts)
        unpaid_invoice_count = sum(int(invoice_rollups.get(a.id, {}).get("unpaid") or 0) for a in accounts)
        overdue_invoice_count = sum(int(invoice_rollups.get(a.id, {}).get("overdue") or 0) for a in accounts)
        total_amount_due_cents = sum(int(invoice_rollups.get(a.id, {}).get("amount_due_cents") or 0) for a in accounts)

        top_due: list[dict[str, Any]] = []
        for row in rows:
            if row.total_amount_due_cents <= 0:
                continue
            top_due.append(
                {
                    "customer_id": row.customer_id,
                    "customer_name": row.customer_name,
                    "amount_due_cents": row.total_amount_due_cents,
                    "overdue_invoice_count": row.overdue_invoice_count,
                }
            )
        top_due.sort(key=lambda x: int(x["amount_due_cents"]), reverse=True)

        xero_conn = self.db.scalars(
            select(SourceSystemConnection)
            .where(SourceSystemConnection.tenant_id == tenant_id, SourceSystemConnection.system_type == "xero")
            .order_by(SourceSystemConnection.updated_at.desc())
            .limit(1)
        ).first()
        xero_last_sync = None
        if xero_conn:
            xero_last_sync = self.db.scalars(
                select(IntegrationSyncRun)
                .where(
                    IntegrationSyncRun.tenant_id == tenant_id,
                    IntegrationSyncRun.source_connection_id == xero_conn.id,
                )
                .order_by(IntegrationSyncRun.created_at.desc())
                .limit(1)
            ).first()

        return {
            "summary": {
                "customer_count": len(customers),
                "finance_linked_count": linked,
                "missing_finance_link_count": missing,
                "orphan_billing_account_count": len(orphan_accounts),
                "unlinked_finance_contact_count": unlinked_finance_contact_count,
                "total_invoice_count": total_invoice_count,
                "unpaid_invoice_count": unpaid_invoice_count,
                "overdue_invoice_count": overdue_invoice_count,
                "total_amount_due_cents": total_amount_due_cents,
                "top_customer_due": top_due[:6],
                "xero_configured": bool(xero_conn),
                "xero_last_sync_status": xero_last_sync.status if xero_last_sync else None,
                "xero_last_sync_completed_at": (
                    xero_last_sync.completed_at.isoformat() if xero_last_sync and xero_last_sync.completed_at else None
                ),
                "underbilling_candidate_count": len(set(underbilling)),
                "overbilling_risk_count": len(set(overbilling_risk)),
                "payment_friction_count": len(set(payment_friction)),
            },
            "coverage_notes": [
                "Finance data connected reflects accounting-side invoices/contacts and mapping coverage.",
                "Payment friction signals are directional and should be reviewed with account context before action.",
                "Revenue assurance checks require service/contract telemetry to confirm true under/overbilling.",
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
            notes.append(
                "Accounting data is not linked for this account yet — treat commercial figures as directional until "
                "finance is connected."
            )
            notes.append(
                "After you connect accounting under Integrations, finish mapping review so invoices roll up to this customer."
            )
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
                "total_invoice_count": 0,
                "unpaid_invoice_count": 0,
                "overdue_invoice_count": 0,
                "total_amount_due_cents": 0,
                "last_invoice_date": None,
                "recent_invoice_lines": [],
                "confidence_level": "low",
                "integrity_highlights": highlights,
                "confidence_notes": notes,
                "next_commercial_action_placeholder": (
                    "Connect accounting and confirm customer mapping before making revenue or margin commitments."
                ),
                "provenance": {"canonical": False},
            }

        snap = self._latest_snapshot(tenant_id, acct.id)
        totals = self._invoice_totals_for_account(tenant_id, acct.id)
        if int(totals["overdue"] or 0) > 0:
            highlights.append(f"{totals['overdue']} overdue invoice(s) need account housekeeping follow-up.")
        if int(totals["amount_due_cents"] or 0) > 0:
            highlights.append("Open receivables present — align billing/admin check-in with account plan.")
        if snap and (snap.aged_outstanding_cents or 0) > 0:
            highlights.append("Aged outstanding balance on latest finance snapshot.")
        if snap and snap.payment_status_summary and snap.payment_status_summary not in ("none", "unknown"):
            highlights.append(f"Invoice friction flag: {snap.payment_status_summary}.")
        if not snap:
            notes.append("Billing account exists but no daily snapshot row yet — run finance sync.")

        line_rows = self.db.scalars(
            select(FinanceInvoiceLine)
            .join(FinanceInvoice, FinanceInvoice.id == FinanceInvoiceLine.invoice_id)
            .where(
                FinanceInvoiceLine.tenant_id == tenant_id,
                FinanceInvoice.billing_account_id == acct.id,
            )
            .order_by(FinanceInvoice.issue_date.desc().nulls_last(), FinanceInvoiceLine.updated_at.desc())
            .limit(5)
        ).all()

        recent_lines = [
            {
                "description": line.description,
                "quantity": float(line.quantity) if line.quantity is not None else None,
                "unit_amount_cents": line.unit_amount_cents,
                "line_total_cents": line.line_total_cents,
                "tax_amount_cents": line.tax_amount_cents,
                "account_code": line.account_code,
            }
            for line in line_rows
        ]

        m365 = self.db.scalars(
            select(M365CustomerPosture).where(
                M365CustomerPosture.tenant_id == tenant_id,
                M365CustomerPosture.customer_id == customer_id,
            )
        ).first()
        if m365:
            if snap and snap.billed_users is not None and m365.active_users_30d is not None and m365.active_users_30d > snap.billed_users + 2:
                highlights.append("M365 active user count is above billed users on latest finance snapshot.")
            if (m365.unused_licences or 0) > 0:
                highlights.append(f"M365 unused licence count: {m365.unused_licences} (optimisation candidate).")
        else:
            notes.append("No M365 linked posture yet — service/contract comparison remains partial.")

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
            "total_invoice_count": int(totals["total"] or 0),
            "unpaid_invoice_count": int(totals["unpaid"] or 0),
            "overdue_invoice_count": int(totals["overdue"] or 0),
            "total_amount_due_cents": int(totals["amount_due_cents"] or 0),
            "last_invoice_date": totals["last_invoice_date"],
            "recent_invoice_lines": recent_lines,
            "confidence_level": snap.confidence_level if snap else "medium",
            "integrity_highlights": highlights,
            "confidence_notes": notes,
            "next_commercial_action_placeholder": (
                "Treat finance points as account housekeeping unless service/contract reconciliation confirms variance."
            ),
            "provenance": {"canonical": True, "extra": acct.extra},
        }
