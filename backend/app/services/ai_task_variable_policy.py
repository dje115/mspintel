"""Task-specific shaping of variables before they are rendered and sent to an LLM.

Full customer AI context includes finance panels, mapping status, connector coverage, etc.
That belongs in operator tools — not in payloads for customer-hearing or strict customer-outbound tasks.

Safety: customer-facing outbound tasks get slimmed/redacted payloads here so models do not echo internal
connector or mapping jargon. This module does **not** change prompt text in the DB; platform prompt sync
remains separate and must not overwrite tenant-owned prompt versions.
"""

from __future__ import annotations

from typing import Any

_TASK_STRICT_CUSTOMER_OUTBOUND = frozenset({
    "customer_review_email_draft",
    "customer_review_report",
})

_TASK_CUSTOMER_HEARING_OR_AM_PREP = frozenset({
    "customer_review_agenda",
    "account_manager_call_script",
    "account_manager_next_conversation",
})

_REDACT_TOP_LEVEL_KEYS = (
    "tenant_profile_context",
    "contacts",
    "open_tickets",
    "recommendation_summaries",
    "recent_actions",
    "open_recommendations",
    "open_opportunities",
    "quotes",
)


def minimal_script_context(sc: dict[str, Any]) -> dict[str, Any]:
    pc = (sc.get("customer") or {}).get("primary_contact")
    primary = None
    if isinstance(pc, dict):
        primary = {k: v for k, v in pc.items() if k in ("name", "email")}
    return {
        "customer": {
            "name": (sc.get("customer") or {}).get("name"),
            "status": (sc.get("customer") or {}).get("status"),
            "owner_name": (sc.get("customer") or {}).get("owner_name"),
            "primary_contact": primary,
        },
        "msp": sc.get("msp"),
        "caller": sc.get("caller"),
    }


def slim_top_level_customer_record(cust: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": cust.get("id"),
        "name": cust.get("name"),
        "status": cust.get("status"),
        "owner_name": cust.get("owner_name"),
    }


def _slim_shared_narrative_variables(variables: dict[str, Any]) -> dict[str, Any]:
    """Drop heavy lists and redact script_context for any task where NL output might reach the customer."""
    out = dict(variables)
    sc = out.get("script_context")
    if isinstance(sc, dict):
        out["script_context"] = minimal_script_context(sc)
    cust = out.get("customer")
    if isinstance(cust, dict):
        out["customer"] = slim_top_level_customer_record(cust)
    for k in _REDACT_TOP_LEVEL_KEYS:
        out.pop(k, None)
    out["missing_data_notes"] = []
    return out


def slim_review_variables_for_customer_facing(full_vars: dict[str, Any]) -> dict[str, Any]:
    """
    Strict outbound customer copy (email + printable report): safe workspace only, no prior AI blobs.
    """
    full_vars = dict(full_vars)
    safe_ws = full_vars.get("review_workspace_customer_safe") or full_vars.get("review_workspace") or {}
    cust_top = full_vars.get("customer") or {}
    out: dict[str, Any] = {
        "customer": slim_top_level_customer_record(cust_top) if isinstance(cust_top, dict) else {},
        "script_context": minimal_script_context(full_vars.get("script_context") or {}),
        "review_workspace": safe_ws,
        "open_counts": full_vars.get("open_counts") or {},
        "email_tone": full_vars.get("email_tone"),
        "missing_data_notes": [],
        "previous_ai_artifacts": [],
        "previous_ai_artifacts_guidance": (
            "Prior AI outputs are omitted for customer-facing artefacts to avoid leaking internal wording. "
            "Rely on review_workspace only."
        ),
    }
    if full_vars.get("task") is not None:
        out["task"] = full_vars["task"]
    return out


def augment_customer_hearing_review_variables(variables: dict[str, Any]) -> dict[str, Any]:
    """
    QBR / call prep: primary `review_workspace` is external-safe; full snapshot under `review_workspace_internal`.
    Prior AI summaries omitted to avoid parroting internal phrasing into customer-hearing fields.
    """
    out = dict(variables)
    safe_ws = out.pop("review_workspace_customer_safe", None)
    full_ws = out.get("review_workspace")
    out = _slim_shared_narrative_variables(out)
    if safe_ws is not None and isinstance(full_ws, dict):
        out["review_workspace_internal"] = dict(full_ws)
        out["review_workspace"] = safe_ws
    elif safe_ws is not None:
        out["review_workspace_internal"] = full_ws
        out["review_workspace"] = safe_ws
    out["previous_ai_artifacts"] = []
    out["previous_ai_artifacts_guidance"] = (
        "Prior AI outputs are omitted here. Use `review_workspace_internal` only for operator-only notes "
        "(internal_only_notes, confidence_notes, data gaps) — never copy that wording into talking points, "
        "opening lines, or customer_safe_topics."
    )
    return out


def prepare_llm_variables(task_type: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of variables suitable for prompt render + model user JSON."""
    if task_type in _TASK_STRICT_CUSTOMER_OUTBOUND:
        return slim_review_variables_for_customer_facing(variables)
    if task_type in _TASK_CUSTOMER_HEARING_OR_AM_PREP:
        return augment_customer_hearing_review_variables(variables)
    return dict(variables)
