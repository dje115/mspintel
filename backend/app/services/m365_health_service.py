from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer, FinanceBillingAccount, FinanceBillingSnapshot, M365CustomerPosture


class M365HealthService:
    def __init__(self, db: Session):
        self.db = db

    def _rows(self, tenant_id: UUID) -> list[M365CustomerPosture]:
        stmt = select(M365CustomerPosture).where(M365CustomerPosture.tenant_id == tenant_id)
        return list(self.db.scalars(stmt).all())

    def _billing_snapshot(self, tenant_id: UUID, customer_id: UUID) -> FinanceBillingSnapshot | None:
        acct = self.db.scalars(
            select(FinanceBillingAccount).where(
                FinanceBillingAccount.tenant_id == tenant_id, FinanceBillingAccount.customer_id == customer_id
            )
        ).first()
        if not acct:
            return None
        return self.db.scalars(
            select(FinanceBillingSnapshot)
            .where(FinanceBillingSnapshot.tenant_id == tenant_id, FinanceBillingSnapshot.billing_account_id == acct.id)
            .order_by(FinanceBillingSnapshot.effective_date.desc(), FinanceBillingSnapshot.created_at.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _billing_impact_signals(p: M365CustomerPosture, snap: FinanceBillingSnapshot | None) -> list[str]:
        signals: list[str] = []
        if snap and snap.billed_users is not None and p.active_users_30d is not None and p.active_users_30d > snap.billed_users + 2:
            signals.append("Active M365 users exceed billed users on finance snapshot.")
        if snap and snap.billed_mailboxes is not None and p.mailbox_count is not None and p.mailbox_count > snap.billed_mailboxes + 2:
            signals.append("Mailbox footprint is above billed mailbox quantity.")
        if (p.unused_licences or 0) >= 3:
            signals.append("Unused licences suggest optimisation opportunity.")
        return signals

    def build_workspace(self, tenant_id: UUID) -> dict[str, Any]:
        customers = list(self.db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all())
        postures = self._rows(tenant_id)
        posture_by_customer = {p.customer_id: p for p in postures}
        out_rows: list[dict[str, Any]] = []
        licensed_total = 0
        active_total = 0
        inactive_total = 0
        mailbox_total = 0
        shared_total = 0
        stale_total = 0
        disabled_total = 0
        opt_count = 0
        billing_mismatch_count = 0
        linked = 0
        for c in customers:
            p = posture_by_customer.get(c.id)
            if not p:
                out_rows.append(
                    {
                        "customer_id": c.id,
                        "customer_name": c.name,
                        "confidence_level": "low",
                        "licensed_users": None,
                        "active_users_30d": None,
                        "inactive_users_30d": None,
                        "disabled_users": None,
                        "stale_users_90d": None,
                        "privileged_admin_users": None,
                        "mailbox_count": None,
                        "shared_mailbox_count": None,
                        "unused_licences": None,
                        "mfa_coverage_pct": None,
                        "tenant_domains": [],
                        "entra_summary": {},
                        "azure_summary": {},
                        "billing_impact_signals": [],
                        "hygiene_findings": [],
                        "optimisation_findings": [],
                        "coverage_notes": ["No canonical M365 posture synced for this customer."],
                    }
                )
                continue
            linked += 1
            licensed_total += p.licensed_users or 0
            active_total += p.active_users_30d or 0
            inactive_total += p.inactive_users_30d or 0
            stale_total += p.stale_users_90d or 0
            disabled_total += p.disabled_users or 0
            mailbox_total += p.mailbox_count or 0
            shared_total += p.shared_mailbox_count or 0
            findings = list(p.optimisation_findings or [])
            if findings:
                opt_count += 1
            notes = [p.coverage_notes] if p.coverage_notes else []
            snap = self._billing_snapshot(tenant_id, c.id)
            billing_signals = self._billing_impact_signals(p, snap)
            if billing_signals:
                billing_mismatch_count += 1
            out_rows.append(
                {
                    "customer_id": c.id,
                    "customer_name": c.name,
                    "confidence_level": p.confidence_level,
                    "licensed_users": p.licensed_users,
                    "active_users_30d": p.active_users_30d,
                    "inactive_users_30d": p.inactive_users_30d,
                    "disabled_users": p.disabled_users,
                    "stale_users_90d": p.stale_users_90d,
                    "privileged_admin_users": p.privileged_admin_users,
                    "mailbox_count": p.mailbox_count,
                    "shared_mailbox_count": p.shared_mailbox_count,
                    "unused_licences": p.unused_licences,
                    "mfa_coverage_pct": float(p.mfa_coverage_pct) if p.mfa_coverage_pct is not None else None,
                    "tenant_domains": list(p.tenant_domains_json or []),
                    "entra_summary": dict(p.entra_summary_json or {}),
                    "azure_summary": dict(p.azure_summary_json or {}),
                    "billing_impact_signals": billing_signals,
                    "hygiene_findings": list(p.hygiene_findings or []),
                    "optimisation_findings": findings,
                    "coverage_notes": notes,
                }
            )
        return {
            "summary": {
                "customer_count": len(customers),
                "linked_count": linked,
                "licensed_users_total": licensed_total,
                "active_users_total": active_total,
                "inactive_users_total": inactive_total,
                "mailbox_total": mailbox_total,
                "shared_mailbox_total": shared_total,
                "stale_users_total": stale_total,
                "disabled_users_total": disabled_total,
                "optimisation_candidate_count": opt_count,
                "billing_mismatch_candidate_count": billing_mismatch_count,
            },
            "coverage_notes": [
                "Microsoft slice is practical but not full Graph security analytics; treat values as operational guidance.",
                "Demo-mode sync materialises seeded profile facts into canonical posture rows unless live read depth is configured.",
            ],
            "customers": out_rows,
        }

    def customer_panel(self, tenant_id: UUID, customer_id: UUID) -> dict[str, Any]:
        p = self.db.scalars(
            select(M365CustomerPosture).where(
                M365CustomerPosture.tenant_id == tenant_id, M365CustomerPosture.customer_id == customer_id
            )
        ).first()
        if not p:
            return {
                "linked": False,
                "confidence_level": "low",
                "licensed_users": None,
                "active_users_30d": None,
                "inactive_users_30d": None,
                "disabled_users": None,
                "stale_users_90d": None,
                "privileged_admin_users": None,
                "mailbox_count": None,
                "shared_mailbox_count": None,
                "unused_licences": None,
                "mfa_coverage_pct": None,
                "tenant_domains": [],
                "entra_summary": {},
                "azure_summary": {},
                "billing_impact_signals": [],
                "hygiene_findings": [],
                "optimisation_findings": [],
                "confidence_notes": ["No canonical M365 posture linked for this account."],
                "next_action_placeholder": "Connect Microsoft 365 / Entra source to improve hygiene and licence confidence.",
            }
        notes = [p.coverage_notes] if p.coverage_notes else []
        snap = self._billing_snapshot(tenant_id, customer_id)
        billing_signals = self._billing_impact_signals(p, snap)
        return {
            "linked": True,
            "confidence_level": p.confidence_level,
            "licensed_users": p.licensed_users,
            "active_users_30d": p.active_users_30d,
            "inactive_users_30d": p.inactive_users_30d,
            "disabled_users": p.disabled_users,
            "stale_users_90d": p.stale_users_90d,
            "privileged_admin_users": p.privileged_admin_users,
            "mailbox_count": p.mailbox_count,
            "shared_mailbox_count": p.shared_mailbox_count,
            "unused_licences": p.unused_licences,
            "mfa_coverage_pct": float(p.mfa_coverage_pct) if p.mfa_coverage_pct is not None else None,
            "tenant_domains": list(p.tenant_domains_json or []),
            "entra_summary": dict(p.entra_summary_json or {}),
            "azure_summary": dict(p.azure_summary_json or {}),
            "billing_impact_signals": billing_signals,
            "hygiene_findings": list(p.hygiene_findings or []),
            "optimisation_findings": list(p.optimisation_findings or []),
            "confidence_notes": notes,
            "next_action_placeholder": (
                "Review inactive/unused identities and validate licence assignment before next billing cycle."
            ),
        }

