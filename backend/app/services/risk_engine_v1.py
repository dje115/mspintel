"""Deterministic heuristic Risk Engine v1 (tenant-scoped, explainable)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AccountScore,
    Contact,
    Customer,
    FinanceBillingAccount,
    FinanceBillingSnapshot,
    Opportunity,
    Quote,
    Recommendation,
    Ticket,
)

RISK_ENGINE_VERSION = "risk_v1"


@dataclass
class RiskFactor:
    code: str
    title: str
    impact_risk: int
    impact_attention: int
    evidence: str

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "impact_risk": self.impact_risk,
            "impact_attention": self.impact_attention,
            "evidence": self.evidence,
        }


class RiskEngineV1Service:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _as_utc(value: datetime | None, fallback: datetime) -> datetime:
        """Normalize mixed DB datetime payloads (sqlite naive vs pg aware)."""
        if value is None:
            return fallback
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

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

    @staticmethod
    def _band(score: int) -> str:
        if score >= 75:
            return "high"
        if score >= 45:
            return "medium"
        return "low"

    def _existing_latest_scores(self, tenant_id: UUID) -> dict[UUID, AccountScore]:
        stmt = (
            select(AccountScore)
            .where(AccountScore.tenant_id == tenant_id)
            .order_by(AccountScore.customer_id, AccountScore.calculated_at.desc(), AccountScore.created_at.desc())
        )
        rows = list(self.db.scalars(stmt).all())
        out: dict[UUID, AccountScore] = {}
        for r in rows:
            if r.customer_id not in out:
                out[r.customer_id] = r
        return out

    def _customer_facts(self, tenant_id: UUID, customer: Customer) -> dict:
        cid = customer.id
        open_tickets = list(
            self.db.scalars(
                select(Ticket)
                .where(Ticket.tenant_id == tenant_id, Ticket.customer_id == cid, Ticket.status == "open")
                .order_by(Ticket.created_at.asc())
            ).all()
        )
        contacts = list(self.db.scalars(select(Contact).where(Contact.tenant_id == tenant_id, Contact.customer_id == cid)).all())
        open_opps = list(
            self.db.scalars(
                select(Opportunity)
                .where(Opportunity.tenant_id == tenant_id, Opportunity.customer_id == cid, Opportunity.status == "open")
                .order_by(Opportunity.created_at.asc())
            ).all()
        )
        quotes = list(
            self.db.scalars(
                select(Quote).where(Quote.tenant_id == tenant_id, Quote.customer_id == cid).order_by(Quote.created_at.desc())
            ).all()
        )
        open_recs = int(
            self.db.scalar(
                select(func.count())
                .select_from(Recommendation)
                .where(
                    Recommendation.tenant_id == tenant_id,
                    Recommendation.customer_id == cid,
                    Recommendation.status == "open",
                )
            )
            or 0
        )
        finance_account = self.db.scalars(
            select(FinanceBillingAccount).where(
                FinanceBillingAccount.tenant_id == tenant_id,
                FinanceBillingAccount.customer_id == cid,
            )
        ).first()
        finance_snapshot = self._latest_snapshot(tenant_id, finance_account.id) if finance_account else None
        return {
            "open_tickets": open_tickets,
            "contacts": contacts,
            "open_opportunities": open_opps,
            "quotes": quotes,
            "has_open_recommendation": open_recs > 0,
            "finance_account": finance_account,
            "finance_snapshot": finance_snapshot,
        }

    def _factors_for_customer(self, customer: Customer, facts: dict) -> tuple[list[RiskFactor], list[str]]:
        factors: list[RiskFactor] = []
        coverage_notes: list[str] = []
        now = datetime.now(UTC)
        open_tickets: list[Ticket] = facts["open_tickets"]
        contacts: list[Contact] = facts["contacts"]
        open_opportunities: list[Opportunity] = facts["open_opportunities"]
        quotes: list[Quote] = facts["quotes"]
        finance_account: FinanceBillingAccount | None = facts["finance_account"]
        finance_snapshot: FinanceBillingSnapshot | None = facts["finance_snapshot"]

        if len(open_tickets) >= 6:
            factors.append(
                RiskFactor(
                    code="high_ticket_volume",
                    title="High open ticket volume",
                    impact_risk=18,
                    impact_attention=12,
                    evidence=f"{len(open_tickets)} open tickets on account.",
                )
            )
        if open_tickets:
            oldest_ticket_ts = self._as_utc(open_tickets[0].created_at, now)
            oldest_days = max(0, int((now - oldest_ticket_ts).total_seconds() // 86400))
            if oldest_days >= 30:
                factors.append(
                    RiskFactor(
                        code="stale_open_ticket",
                        title="Stale open ticket(s)",
                        impact_risk=15,
                        impact_attention=10,
                        evidence=f"Oldest open ticket age is {oldest_days} days.",
                    )
                )
        rel = (customer.demo_profile or {}).get("relationship") or {}
        qbr_days = rel.get("last_qbr_days_ago")
        if isinstance(qbr_days, int) and qbr_days >= 180:
            factors.append(
                RiskFactor(
                    code="no_recent_review",
                    title="No recent QBR/review cadence",
                    impact_risk=10,
                    impact_attention=12,
                    evidence=f"Last review captured at {qbr_days} days ago.",
                )
            )
        elif qbr_days is None:
            coverage_notes.append("No structured review recency on record.")
        stakeholder_count = rel.get("stakeholder_count")
        if isinstance(stakeholder_count, int) and stakeholder_count <= 1:
            factors.append(
                RiskFactor(
                    code="weak_stakeholder_coverage",
                    title="Weak stakeholder coverage",
                    impact_risk=7,
                    impact_attention=9,
                    evidence=f"Only {stakeholder_count} stakeholder(s) recorded.",
                )
            )
        if len(contacts) < 2:
            factors.append(
                RiskFactor(
                    code="low_contact_coverage",
                    title="Low contact coverage",
                    impact_risk=8,
                    impact_attention=10,
                    evidence=f"{len(contacts)} contact(s) known in canonical CRM slice.",
                )
            )
        if not finance_account:
            factors.append(
                RiskFactor(
                    code="no_finance_link",
                    title="No linked finance account",
                    impact_risk=10,
                    impact_attention=6,
                    evidence="Canonical finance link is missing.",
                )
            )
            coverage_notes.append("Finance linkage missing; commercial risk confidence is reduced.")
        elif not finance_snapshot:
            coverage_notes.append("Finance account linked but no billing snapshot available yet.")
        else:
            bm = finance_snapshot.billed_mailboxes
            sm = finance_snapshot.service_active_mailboxes
            if bm is not None and sm is not None and sm > bm + 1:
                factors.append(
                    RiskFactor(
                        code="billing_mismatch",
                        title="Billing/service mismatch",
                        impact_risk=12,
                        impact_attention=10,
                        evidence=f"Service mailboxes {sm} exceed billed mailboxes {bm}.",
                    )
                )
            if (finance_snapshot.aged_outstanding_cents or 0) > 0 or (
                finance_snapshot.payment_status_summary and finance_snapshot.payment_status_summary not in ("none", "unknown")
            ):
                factors.append(
                    RiskFactor(
                        code="payment_friction",
                        title="Payment friction or aged debt",
                        impact_risk=14,
                        impact_attention=9,
                        evidence=(
                            f"payment_status={finance_snapshot.payment_status_summary}, "
                            f"aged_outstanding_cents={finance_snapshot.aged_outstanding_cents or 0}"
                        ),
                    )
                )
        if not open_opportunities:
            has_recent_quote = any(q.created_at and (now - q.created_at).days < 120 for q in quotes)
            if not has_recent_quote:
                factors.append(
                    RiskFactor(
                        code="no_recent_commercial_movement",
                        title="No recent commercial movement",
                        impact_risk=4,
                        impact_attention=9,
                        evidence="No open opportunities and no recent quote activity in 120 days.",
                    )
                )
        else:
            oldest_opp_ts = self._as_utc(open_opportunities[0].created_at, now)
            oldest_opp_days = max(0, int((now - oldest_opp_ts).total_seconds() // 86400))
            if oldest_opp_days >= 120:
                factors.append(
                    RiskFactor(
                        code="stalled_opportunity",
                        title="Stalled open opportunity",
                        impact_risk=6,
                        impact_attention=10,
                        evidence=f"Oldest open opportunity age is {oldest_opp_days} days.",
                    )
                )
        lost_quotes = [q for q in quotes if (q.status or "").lower() == "lost"]
        if len(lost_quotes) >= 2:
            factors.append(
                RiskFactor(
                    code="stalled_quote",
                    title="Repeated lost quotes",
                    impact_risk=5,
                    impact_attention=8,
                    evidence=f"{len(lost_quotes)} lost quote(s) on account.",
                )
            )
        if len(open_tickets) >= 4 and not open_opportunities:
            factors.append(
                RiskFactor(
                    code="service_burden_out_of_line",
                    title="Service burden out of line with commercial momentum",
                    impact_risk=8,
                    impact_attention=8,
                    evidence="High ticket load with no open commercial movement.",
                )
            )
        if not customer.owner_name and not customer.external_ref and len(contacts) == 0:
            factors.append(
                RiskFactor(
                    code="sparse_customer_data",
                    title="Sparse customer data",
                    impact_risk=6,
                    impact_attention=6,
                    evidence="Missing owner/external ref and no contacts linked.",
                )
            )
            coverage_notes.append("Sparse customer profile fields reduce confidence.")
        return factors, coverage_notes

    def score_customer(self, tenant_id: UUID, customer: Customer) -> AccountScore:
        facts = self._customer_facts(tenant_id, customer)
        factors, coverage_notes = self._factors_for_customer(customer, facts)
        risk = 12 + sum(max(0, f.impact_risk) for f in factors)
        attention = 10 + sum(max(0, f.impact_attention) for f in factors)
        if facts["has_open_recommendation"]:
            attention += 4
        risk = min(100, max(0, int(risk)))
        attention = min(100, max(0, int(attention)))
        confidence_raw = 1.0
        finance_snapshot: FinanceBillingSnapshot | None = facts["finance_snapshot"]
        if any(f.code == "no_finance_link" for f in factors):
            confidence_raw -= 0.25
        elif finance_snapshot and (finance_snapshot.confidence_level or "").lower() != "high":
            confidence_raw -= 0.15
        if any(f.code == "sparse_customer_data" for f in factors):
            confidence_raw -= 0.20
        if any("No structured review recency" in n for n in coverage_notes):
            confidence_raw -= 0.10
        confidence = "high" if confidence_raw >= 0.9 else ("medium" if confidence_raw >= 0.55 else "low")
        if risk >= 70:
            customer.status = "at_risk"
        elif attention >= 55 or risk >= 45:
            customer.status = "watch"
        else:
            customer.status = "active"
        row = AccountScore(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            customer_id=customer.id,
            risk_score=risk,
            attention_score=attention,
            growth_score=0,
            risk_level=self._band(risk),
            attention_level=self._band(attention),
            confidence_level=confidence,
            scoring_version=RISK_ENGINE_VERSION,
            reason_codes=[f.code for f in factors],
            factors_json=[f.as_dict() for f in factors],
            coverage_notes=coverage_notes,
            calculated_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def recompute_customer(self, tenant_id: UUID, customer_id: UUID) -> AccountScore:
        customer = self.db.scalars(select(Customer).where(Customer.tenant_id == tenant_id, Customer.id == customer_id)).first()
        if not customer:
            raise ValueError("Customer not found")
        return self.score_customer(tenant_id, customer)

    def recompute_tenant(self, tenant_id: UUID) -> dict:
        customers = list(self.db.scalars(select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.name)).all())
        if not customers:
            return {"processed": 0, "scoring_version": RISK_ENGINE_VERSION}
        processed = 0
        for c in customers:
            self.score_customer(tenant_id, c)
            processed += 1
        self.db.flush()
        return {"processed": processed, "scoring_version": RISK_ENGINE_VERSION}

    def ensure_scores(self, tenant_id: UUID) -> None:
        has_any = self.db.scalars(select(AccountScore.id).where(AccountScore.tenant_id == tenant_id).limit(1)).first()
        if not has_any:
            self.recompute_tenant(tenant_id)

    def latest_score_for_customer(self, tenant_id: UUID, customer_id: UUID) -> AccountScore | None:
        self.ensure_scores(tenant_id)
        stmt = (
            select(AccountScore)
            .where(AccountScore.tenant_id == tenant_id, AccountScore.customer_id == customer_id)
            .order_by(AccountScore.calculated_at.desc(), AccountScore.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def latest_scores_map(self, tenant_id: UUID) -> dict[UUID, AccountScore]:
        self.ensure_scores(tenant_id)
        return self._existing_latest_scores(tenant_id)

