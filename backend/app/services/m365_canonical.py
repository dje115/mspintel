from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer, M365CustomerPosture


def _norm_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _confidence_from_profile(profile: dict | None) -> str:
    dq = (profile or {}).get("data_quality") or {}
    confidence = str(dq.get("confidence") or "medium").lower()
    if confidence in {"high", "medium", "low"}:
        return confidence
    if confidence in {"medium_low", "medium-low"}:
        return "medium"
    return "medium"


def upsert_m365_for_customer(
    db: Session,
    *,
    tenant_id: UUID,
    customer_id: UUID,
    demo_profile: dict | None,
    source_connection_id: UUID | None,
    provenance: str,
) -> M365CustomerPosture | None:
    m365 = (demo_profile or {}).get("microsoft_365") or {}
    if not m365:
        return None
    stmt = select(M365CustomerPosture).where(
        M365CustomerPosture.tenant_id == tenant_id,
        M365CustomerPosture.customer_id == customer_id,
    )
    row = db.scalars(stmt).first()
    if not row:
        row = M365CustomerPosture(
            tenant_id=tenant_id,
            customer_id=customer_id,
            source_connection_id=source_connection_id,
            measured_at=datetime.now(UTC),
        )
        db.add(row)
        db.flush()

    licensed = _norm_int(m365.get("licensed_users"))
    active = _norm_int(m365.get("active_sign_ins_30d"))
    mailboxes = active
    shared_mailboxes = _norm_int(m365.get("shared_mailboxes"))
    if shared_mailboxes is None and mailboxes is not None:
        shared_mailboxes = max(0, int(mailboxes * 0.08))
    inactive = None
    if licensed is not None and active is not None:
        inactive = max(0, licensed - active)

    hygiene = [str(m365.get("hygiene"))] if m365.get("hygiene") else []
    opt: list[str] = []
    unused = _norm_int(m365.get("unused_licences"))
    if unused and unused > 0:
        opt.append(f"{unused} potentially unused licence(s) to review.")
    if shared_mailboxes and shared_mailboxes >= 10:
        opt.append("Shared mailbox count is high; validate ownership/lifecycle.")

    row.source_connection_id = source_connection_id or row.source_connection_id
    row.external_tenant_ref = str((demo_profile or {}).get("city_line") or "")[:180] or row.external_tenant_ref
    row.tenant_display_name = None
    row.domain_name = None
    row.licensed_users = licensed
    row.active_users_30d = active
    row.inactive_users_30d = inactive
    row.mailbox_count = mailboxes
    row.shared_mailbox_count = shared_mailboxes
    row.unused_licences = unused
    mfa = m365.get("mfa_coverage_pct")
    row.mfa_coverage_pct = Decimal(str(mfa)) if mfa is not None else None
    row.licence_summary_json = [{"sku": "Microsoft 365", "assigned_users": licensed, "unused": unused}]
    row.hygiene_findings = hygiene
    row.optimisation_findings = opt
    row.confidence_level = _confidence_from_profile(demo_profile)
    row.coverage_notes = (
        "Materialised from demo profile connector path; live Graph/Azure read depth is intentionally limited in v1."
    )
    row.measured_at = datetime.now(UTC)
    row.extra = {"provenance": provenance}
    db.flush()
    return row

