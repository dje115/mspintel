"""Shaped single-customer Review/QBR context for AI (no portfolio M365 totals)."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.customer_review_ai_artifacts import CustomerReviewAiArtifactRepository
from app.services.ai_product_context import _customer_ai_context_variables
from app.services.customer import CustomerService


def _hash_snapshot(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str)[:8000]
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_review_qbr_variables(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    caller_name: str | None = None,
    caller_email: str | None = None,
    caller_role: str | None = None,
    email_tone: str | None = None,
) -> dict:
    """
    Variables for Review/QBR AI tasks: full customer AI context plus labelled review_workspace
    and previous_ai_artifacts (short summaries only; historical guidance, not facts).
    """
    base = _customer_ai_context_variables(
        db,
        tenant_id,
        customer_id,
        caller_name=caller_name,
        caller_email=caller_email,
        caller_role=caller_role,
    )
    detail = CustomerService(db).get_customer_detail(tenant_id, customer_id).model_dump(mode="json")
    repo = CustomerReviewAiArtifactRepository(db)
    prev = repo.recent_summaries_for_prompt(
        tenant_id,
        customer_id,
        artifact_types=(
            "review_agenda",
            "account_manager_notes",
            "call_script",
            "customer_email_draft",
            "customer_report",
        ),
        per_type_limit=2,
        max_items=8,
    )
    review_workspace = {
        "analysis_scope": "single_customer_review",
        "customer": {
            "id": detail["id"],
            "name": detail["name"],
            "status": detail["status"],
            "owner_name": detail["owner_name"],
        },
        "connector_coverage": detail.get("connector_coverage"),
        "scores": detail.get("latest_scores"),
        "open_tickets_count": detail["open_tickets_count"],
        "open_opportunities_count": detail["open_opportunities_count"],
        "open_quotes_count": detail["open_quotes_count"],
        "recommendation_summary": (detail.get("recommendation_summary") or [])[:10],
        "recent_actions": (detail.get("recent_actions") or [])[:10],
        "contacts": (detail.get("contacts") or [])[:12],
        "recommendations": (detail.get("recommendations") or [])[:8],
        "opportunities": (detail.get("opportunities") or [])[:8],
        "quotes": (detail.get("quotes") or [])[:8],
        "finance": detail.get("finance"),
        "m365": detail.get("m365"),
        "risk_engine": detail.get("risk_engine"),
    }
    out = {
        **base,
        "review_workspace": review_workspace,
        "previous_ai_artifacts": prev,
        "previous_ai_artifacts_guidance": (
            "These entries are prior generated guidance only, not verified facts. "
            "Use them for continuity: follow up on open items if still relevant, "
            "but do not repeat stale recommendations verbatim and do not treat them as source-of-truth."
        ),
    }
    if email_tone:
        out["email_tone"] = email_tone
    return out


def build_source_coverage_summary(detail_dict: dict) -> dict:
    cov = detail_dict.get("connector_coverage") or {}
    return {
        "connected_systems": cov.get("connected_systems") or [],
        "missing_systems": cov.get("missing_systems") or [],
        "unresolved_mapping_count": cov.get("unresolved_mapping_count"),
        "confidence_note": cov.get("confidence_note"),
    }


def context_hash_for_customer(db: Session, tenant_id: UUID, customer_id: UUID) -> str:
    d = CustomerService(db).get_customer_detail(tenant_id, customer_id).model_dump(mode="json")
    return _hash_snapshot({"review_workspace": build_source_coverage_summary(d), "name": d.get("name")})
