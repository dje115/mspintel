"""Shaped single-customer Review/QBR context for AI (no portfolio M365 totals)."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Ticket
from app.repositories.customer_review_ai_artifacts import CustomerReviewAiArtifactRepository
from app.services.ai_product_context import _customer_ai_context_variables
from app.services.customer import CustomerService


def _hash_snapshot(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str)[:8000]
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_customer_safe_review_workspace(detail: dict, *, script_context: dict) -> dict:
    """
    Minimal, external-safe context for customer email / printable report generation.

    Must not expose connector names, sync/mapping state, product internals, or data-import status —
    those belong in operator-only artefacts (agenda, AM notes, internal panels).
    """
    name = (detail.get("name") or "").strip() or "your organisation"
    sc = script_context or {}
    caller = sc.get("caller") or {}
    sign_raw = (caller.get("name") or "").strip()
    if sign_raw.lower() in ("your account manager", "your account team"):
        sign_raw = ""
    msp = sc.get("msp") or {}
    brand = (msp.get("brand_name") or "").strip() or "our team"

    hooks: list[str] = []
    if (detail.get("open_tickets_count") or 0) > 0:
        hooks.append("Review recent service themes and how we can support you best.")
    if (detail.get("open_opportunities_count") or 0) > 0:
        hooks.append("Align on open opportunities and sensible next steps.")
    if (detail.get("open_quotes_count") or 0) > 0:
        hooks.append("Touch base on any proposals or quotes you may want to progress.")
    fin = detail.get("finance") or {}
    if fin.get("finance_linked"):
        hooks.append(
            "At a high level, we can align on account housekeeping and billing topics — "
            "keep wording general; do not quote dashboards, systems, or linkage status."
        )
    else:
        hooks.append(
            "Keep finance discussion qualitative unless the customer raises specifics — "
            "do not mention missing records, tools, or internal data completeness."
        )

    return {
        "audience": "external_customer_recipient",
        "voice": (
            "You represent the MSP writing to the customer. Be warm and professional. "
            "The customer does not use our internal platform — never mention imports, sync, mappings, "
            "connectors, integrations setup, accounting product names, or 'linkage' / 'canonical' data. "
            "Never instruct the customer to perform internal admin tasks."
        ),
        "customer": {"name": name},
        "msp": {"brand_name": brand},
        "sign_off": {
            "account_manager_name": sign_raw or None,
            "instruction": (
                "End with 'Best regards,' then the account manager's real first and last name if provided above; "
                "otherwise 'Best regards,' followed by the MSP brand name alone. "
                "Forbidden: [Your Name], [Customer Name], or any bracket placeholder."
            ),
        },
        "suggested_discussion_hooks": hooks[:8],
        "never_include_terms": [
            "Xero",
            "sync",
            "mapping",
            "connector",
            "integration",
            "MSPIntel",
            "canonical",
            "import",
            "billing account",
            "data completeness",
            "unresolved",
        ],
    }


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
    open_ticket_rows = list(
        db.scalars(
            select(Ticket)
            .where(Ticket.tenant_id == tenant_id, Ticket.customer_id == customer_id, Ticket.status == "open")
            .order_by(Ticket.updated_at.desc().nulls_last(), Ticket.created_at.desc())
            .limit(10)
        ).all()
    )
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
        "finance_internal_notes": {
            "tone_guidance": (
                "Treat unpaid/overdue invoices as internal account-housekeeping context. "
                "Avoid accusatory customer-facing language unless finance has confirmed an agreed escalation path."
            ),
            "service_reconciliation_note": (
                "Revenue assurance conclusions require service/contract telemetry in addition to accounting rows."
            ),
        },
        "m365": detail.get("m365"),
        "risk_engine": detail.get("risk_engine"),
        "open_tickets": [
            {
                "subject": row.subject,
                "status": row.status,
                "external_ref": row.external_ref,
            }
            for row in open_ticket_rows
        ],
    }
    review_workspace_customer_safe = build_customer_safe_review_workspace(detail, script_context=base["script_context"])
    out = {
        **base,
        "review_workspace": review_workspace,
        "review_workspace_customer_safe": review_workspace_customer_safe,
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
