"""Tenant backup / BCDR workspace (multi-vendor facts + AI variables)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BackupConnectionPanel(BaseModel):
    connection_id: UUID
    display_name: str
    vendor_system_type: str
    health_status: str
    lifecycle_state: str
    last_sync_status: str | None = None
    last_sync_completed_at: datetime | None = None
    fact_counts: dict[str, int] = Field(default_factory=dict)


class BackupCustomerRollup(BaseModel):
    customer_id: UUID | None = None
    customer_name: str | None = None
    mapped: bool
    job_count: int = 0
    workload_count: int = 0
    unprotected_workloads: int = 0
    failed_or_warning_jobs: int = 0
    signals_sample: list[str] = Field(default_factory=list)


class BackupHealthWorkspaceResponse(BaseModel):
    summary: dict[str, Any]
    coverage_notes: list[str]
    connections: list[BackupConnectionPanel]
    customer_rollups: list[BackupCustomerRollup]
    fact_samples: list[dict[str, Any]]
