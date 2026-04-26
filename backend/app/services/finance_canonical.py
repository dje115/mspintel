"""Upsert canonical finance rows from structured demo profile or connector sync."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import FinanceBillingAccount, FinanceBillingSnapshot, FinanceInvoice


def _gbp_to_cents(amount_gbp: Any) -> int | None:
    if amount_gbp is None:
        return None
    try:
        return int(round(float(amount_gbp) * 100))
    except (TypeError, ValueError):
        return None


def upsert_finance_for_customer(
    db: Session,
    *,
    tenant_id: UUID,
    customer_id: UUID,
    customer_name: str,
    demo_profile: dict[str, Any] | None,
    source_connection_id: UUID | None,
    provenance: str = "demo_seed",
) -> FinanceBillingAccount | None:
    """Create or refresh billing account + snapshot + sample invoices from ``demo_profile`` billing/M365 slices."""
    if not demo_profile:
        return None
    billing = demo_profile.get("billing") or {}
    m365 = demo_profile.get("microsoft_365") or {}
    if not billing and not m365:
        return None

    ext_id = f"canonical:{customer_id}"
    stmt = select(FinanceBillingAccount).where(
        FinanceBillingAccount.tenant_id == tenant_id,
        FinanceBillingAccount.external_billing_account_id == ext_id,
    )
    row = db.scalars(stmt).first()
    currency = (billing.get("currency") or "GBP") if isinstance(billing.get("currency"), str) else "GBP"
    display_name = f"{customer_name} — billing"
    if row:
        row.customer_id = customer_id
        row.source_connection_id = source_connection_id
        row.display_name = display_name[:220]
        row.currency_code = currency[:12]
        row.linkage_status = "linked" if customer_id else "orphan"
        row.coverage_notes = (
            "Synthetic finance slice aligned to demo seed; not a live accounting ledger."
            if demo_profile.get("synthetic")
            else None
        )
        row.extra = {"provenance": provenance, "source_sim": billing.get("source_sim")}
    else:
        row = FinanceBillingAccount(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            customer_id=customer_id,
            source_connection_id=source_connection_id,
            external_billing_account_id=ext_id,
            display_name=display_name[:220],
            currency_code=currency[:12],
            linkage_status="linked",
            coverage_notes=(
                "Synthetic finance slice aligned to demo seed; not a live accounting ledger."
                if demo_profile.get("synthetic")
                else None
            ),
            extra={"provenance": provenance, "source_sim": billing.get("source_sim")},
        )
        db.add(row)
    db.flush()

    billed_seats = billing.get("billed_m365_seats")
    mailboxes = billing.get("active_mailboxes_measured")
    storage_billed = billing.get("storage_tb_billed")
    licensed = m365.get("licensed_users")
    # Demo seed: ``billed_m365_seats`` is the finance-side billed count; ``active_mailboxes_measured`` is the service read.
    billed_mailbox_proxy = int(billed_seats) if billed_seats is not None else None
    service_mailbox_measured = int(mailboxes) if mailboxes is not None else None

    aged = _gbp_to_cents(billing.get("aged_debt_gbp")) or 0
    friction = str(billing.get("invoice_friction") or "unknown")

    snap_date = date.today()
    snap_stmt = select(FinanceBillingSnapshot).where(
        FinanceBillingSnapshot.billing_account_id == row.id,
        FinanceBillingSnapshot.effective_date == snap_date,
    )
    snap = db.scalars(snap_stmt).first()
    conf = str(demo_profile.get("data_quality", {}).get("confidence") or "medium")
    if conf not in ("high", "medium", "medium_low", "low"):
        conf = "medium"

    snap_fields = dict(
        tenant_id=tenant_id,
        billing_account_id=row.id,
        source_connection_id=source_connection_id,
        effective_date=snap_date,
        billed_users=int(billed_seats) if billed_seats is not None else None,
        billed_mailboxes=billed_mailbox_proxy,
        billed_devices=None,
        billed_storage_tb=Decimal(str(storage_billed)) if storage_billed is not None else None,
        service_licensed_users=int(licensed) if licensed is not None else None,
        service_active_mailboxes=service_mailbox_measured,
        mrr_cents=None,
        payment_status_summary=friction[:80],
        aged_outstanding_cents=aged,
        confidence_level="high" if conf == "high" else ("low" if "low" in conf else "medium"),
        coverage_notes="Counts reflect demo seed billing vs M365 blocks; reconcile in PSA/finance for production.",
    )
    if snap:
        for k, v in snap_fields.items():
            setattr(snap, k, v)
    else:
        snap = FinanceBillingSnapshot(id=uuid.uuid4(), **snap_fields)
        db.add(snap)
    db.flush()

    # Two lightweight invoice summaries (not full AR)
    inv_specs: list[tuple[str, str, int, int]] = [
        ("INV-SEED-1", "authorised", 120000, 0),
        ("INV-SEED-2", "paid", 85000, 0),
    ]
    if aged > 0:
        inv_specs.append(("INV-SEED-AR", "authorised", aged, aged))

    today = date.today()
    for ext_inv, st, total, out in inv_specs:
        inv_q = select(FinanceInvoice).where(
            FinanceInvoice.tenant_id == tenant_id,
            FinanceInvoice.billing_account_id == row.id,
            FinanceInvoice.external_invoice_id == ext_inv,
        )
        inv = db.scalars(inv_q).first()
        fields = dict(
            tenant_id=tenant_id,
            billing_account_id=row.id,
            source_connection_id=source_connection_id,
            external_invoice_id=ext_inv,
            status=st,
            total_cents=total,
            outstanding_cents=out,
            currency_code=currency[:12],
            issue_date=today - timedelta(days=28),
            due_date=today + timedelta(days=32),
            extra={"synthetic": True},
        )
        if inv:
            for k, v in fields.items():
                setattr(inv, k, v)
        else:
            db.add(FinanceInvoice(id=uuid.uuid4(), **fields))
    db.flush()
    return row

