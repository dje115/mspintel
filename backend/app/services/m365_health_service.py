from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer, M365CustomerPosture


class M365HealthService:
    def __init__(self, db: Session):
        self.db = db

    def _rows(self, tenant_id: UUID) -> list[M365CustomerPosture]:
        stmt = select(M365CustomerPosture).where(M365CustomerPosture.tenant_id == tenant_id)
        return list(self.db.scalars(stmt).all())

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
        opt_count = 0
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
                        "mailbox_count": None,
                        "shared_mailbox_count": None,
                        "unused_licences": None,
                        "mfa_coverage_pct": None,
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
            mailbox_total += p.mailbox_count or 0
            shared_total += p.shared_mailbox_count or 0
            findings = list(p.optimisation_findings or [])
            if findings:
                opt_count += 1
            notes = [p.coverage_notes] if p.coverage_notes else []
            out_rows.append(
                {
                    "customer_id": c.id,
                    "customer_name": c.name,
                    "confidence_level": p.confidence_level,
                    "licensed_users": p.licensed_users,
                    "active_users_30d": p.active_users_30d,
                    "inactive_users_30d": p.inactive_users_30d,
                    "mailbox_count": p.mailbox_count,
                    "shared_mailbox_count": p.shared_mailbox_count,
                    "unused_licences": p.unused_licences,
                    "mfa_coverage_pct": float(p.mfa_coverage_pct) if p.mfa_coverage_pct is not None else None,
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
                "optimisation_candidate_count": opt_count,
            },
            "coverage_notes": [
                "M365 slice v1 is intentionally thin. Values are directional and depend on connector coverage.",
                "Demo-mode sync materialises seeded profile facts into canonical posture rows.",
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
                "mailbox_count": None,
                "shared_mailbox_count": None,
                "unused_licences": None,
                "mfa_coverage_pct": None,
                "hygiene_findings": [],
                "optimisation_findings": [],
                "confidence_notes": ["No canonical M365 posture linked for this account."],
                "next_action_placeholder": "Connect Microsoft 365 / Entra source to improve hygiene and licence confidence.",
            }
        notes = [p.coverage_notes] if p.coverage_notes else []
        return {
            "linked": True,
            "confidence_level": p.confidence_level,
            "licensed_users": p.licensed_users,
            "active_users_30d": p.active_users_30d,
            "inactive_users_30d": p.inactive_users_30d,
            "mailbox_count": p.mailbox_count,
            "shared_mailbox_count": p.shared_mailbox_count,
            "unused_licences": p.unused_licences,
            "mfa_coverage_pct": float(p.mfa_coverage_pct) if p.mfa_coverage_pct is not None else None,
            "hygiene_findings": list(p.hygiene_findings or []),
            "optimisation_findings": list(p.optimisation_findings or []),
            "confidence_notes": notes,
            "next_action_placeholder": (
                "Review inactive/unused identities and validate licence assignment before next billing cycle."
            ),
        }

