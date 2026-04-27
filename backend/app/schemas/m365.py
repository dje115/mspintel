from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class M365WorkspaceSummary(BaseModel):
    customer_count: int
    linked_count: int
    licensed_users_total: int
    active_users_total: int
    inactive_users_total: int
    mailbox_total: int
    shared_mailbox_total: int
    stale_users_total: int
    disabled_users_total: int
    optimisation_candidate_count: int
    billing_mismatch_candidate_count: int


class M365WorkspaceRow(BaseModel):
    customer_id: UUID
    customer_name: str
    confidence_level: str
    licensed_users: int | None
    active_users_30d: int | None
    inactive_users_30d: int | None
    disabled_users: int | None
    stale_users_90d: int | None
    privileged_admin_users: int | None
    mailbox_count: int | None
    shared_mailbox_count: int | None
    unused_licences: int | None
    mfa_coverage_pct: float | None
    tenant_domains: list[str] = Field(default_factory=list)
    entra_summary: dict = Field(default_factory=dict)
    azure_summary: dict = Field(default_factory=dict)
    billing_impact_signals: list[str] = Field(default_factory=list)
    hygiene_findings: list[str] = Field(default_factory=list)
    optimisation_findings: list[str] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)


class M365WorkspaceResponse(BaseModel):
    summary: M365WorkspaceSummary
    coverage_notes: list[str] = Field(default_factory=list)
    customers: list[M365WorkspaceRow] = Field(default_factory=list)


class M365CustomerPanel(BaseModel):
    linked: bool
    confidence_level: str
    licensed_users: int | None
    active_users_30d: int | None
    inactive_users_30d: int | None
    disabled_users: int | None
    stale_users_90d: int | None
    privileged_admin_users: int | None
    mailbox_count: int | None
    shared_mailbox_count: int | None
    unused_licences: int | None
    mfa_coverage_pct: float | None
    tenant_domains: list[str] = Field(default_factory=list)
    entra_summary: dict = Field(default_factory=dict)
    azure_summary: dict = Field(default_factory=dict)
    billing_impact_signals: list[str] = Field(default_factory=list)
    hygiene_findings: list[str] = Field(default_factory=list)
    optimisation_findings: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    next_action_placeholder: str

