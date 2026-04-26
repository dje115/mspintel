from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BillingIntegritySummary(BaseModel):
    customer_count: int
    finance_linked_count: int
    missing_finance_link_count: int
    orphan_billing_account_count: int
    underbilling_candidate_count: int
    overbilling_risk_count: int
    payment_friction_count: int


class BillingIntegrityAccountRow(BaseModel):
    customer_id: UUID
    customer_name: str
    finance_linked: bool
    billed_mailboxes: int | None = None
    service_mailboxes: int | None = None
    billed_users: int | None = None
    service_licensed_users: int | None = None
    payment_friction: str | None = None
    aged_outstanding_cents: int | None = None
    confidence_level: str | None = None
    signals: list[str] = Field(default_factory=list)


class BillingIntegrityWorkspaceResponse(BaseModel):
    summary: BillingIntegritySummary
    coverage_notes: list[str]
    accounts: list[BillingIntegrityAccountRow]


class FinanceCustomerPanel(BaseModel):
    finance_linked: bool
    billing_account_id: UUID | None = None
    display_name: str | None = None
    currency_code: str | None = None
    snapshot_effective_date: str | None = None
    billed_mailboxes: int | None = None
    service_active_mailboxes: int | None = None
    billed_users: int | None = None
    service_licensed_users: int | None = None
    payment_status_summary: str | None = None
    aged_outstanding_cents: int | None = None
    confidence_level: str | None = None
    integrity_highlights: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    next_commercial_action_placeholder: str = (
        "Reconcile billed quantities with PSA contracts and latest entitlement review."
    )
    provenance: dict[str, Any] | None = None
