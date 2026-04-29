"""Structured variables for product AI tasks (JSON-serializable)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Contact, SourceEntityMapping, Ticket
from app.models.entities import ConnectorMappingReview, IntegrationSyncRun, SourceSystemConnection
from app.repositories.customers import CustomerRepository
from app.repositories.workspace import WorkspaceRepository
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.m365_health_service import M365HealthService
from app.services.risk_engine_v1 import RiskEngineV1Service
from app.services.tenant_profile import build_tenant_ai_context
from app.services.workspace import WorkspaceService


def _customer_ai_context_variables(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    caller_name: str | None = None,
    caller_email: str | None = None,
    caller_role: str | None = None,
) -> dict:
    repo = CustomerRepository(db)
    customer = repo.get_customer(tenant_id, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    score = repo.latest_score(tenant_id, customer_id)
    tickets, opps, quotes = repo.open_counts(tenant_id, customer_id)
    rec_summaries = repo.recommendation_summary(tenant_id, customer_id)
    actions = repo.recent_actions(tenant_id, customer_id)
    contacts = list(
        db.scalars(
            select(Contact)
            .where(Contact.tenant_id == tenant_id, Contact.customer_id == customer_id)
            .order_by(Contact.name.asc())
            .limit(20)
        ).all()
    )
    open_ticket_rows = list(
        db.scalars(
            select(Ticket)
            .where(Ticket.tenant_id == tenant_id, Ticket.customer_id == customer_id, Ticket.status == "open")
            .order_by(Ticket.created_at.asc())
            .limit(12)
        ).all()
    )
    ws = WorkspaceService(db)
    rec_rows, opp_rows, quote_rows = ws.customer_workspace_slices(tenant_id, customer_id)
    fin = BillingIntegrityService(db).customer_finance_panel(tenant_id, customer_id)
    m365 = M365HealthService(db).customer_panel(tenant_id, customer_id)
    risk = RiskEngineV1Service(db).latest_score_for_customer(tenant_id, customer_id)
    if fin.get("error") == "not_found":
        fin = {}
    tenant_profile_context = build_tenant_ai_context(db, tenant_id).model_dump(mode="json")
    customer_mappings = list(
        db.scalars(
            select(SourceEntityMapping).where(
                SourceEntityMapping.tenant_id == tenant_id,
                SourceEntityMapping.entity_type == "customer",
                SourceEntityMapping.canonical_entity_id == customer_id,
            )
        ).all()
    )
    primary_contact = contacts[0] if contacts else None
    caller_display_name = caller_name or "your account manager"
    msp_profile = dict(tenant_profile_context.get("msp_profile_summary") or {})
    msp_brand_name = msp_profile.get("brand_name") or msp_profile.get("legal_name") or "your MSP team"
    missing_data_notes: list[str] = []
    if not customer.owner_name:
        missing_data_notes.append("Account owner is not set on this customer.")
    if primary_contact is None:
        missing_data_notes.append("No primary contact is available from synced customer contacts.")
    if not customer_mappings:
        missing_data_notes.append("No source mapping rows were found for this canonical customer.")
    if not m365.get("linked"):
        missing_data_notes.append("M365 posture is not linked for this customer.")
    if not risk:
        missing_data_notes.append("Risk Engine snapshot is unavailable for this customer.")
    if not fin:
        missing_data_notes.append("Finance linkage context is unavailable for this customer.")
    script_context = {
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "status": customer.status,
            "owner_name": customer.owner_name,
            "primary_contact": {
                "name": primary_contact.name,
                "email": primary_contact.email,
                "external_ref": primary_contact.external_ref,
            }
            if primary_contact
            else None,
            "mapping_status": "mapped" if customer_mappings else "unmapped",
            "mapping_confidence": m365.get("confidence_level") or (risk.confidence_level if risk else "low"),
            "mapping_count": len(customer_mappings),
        },
        "msp": {
            "brand_name": msp_brand_name,
            "legal_name": msp_profile.get("legal_name"),
            "regions_served": list(tenant_profile_context.get("regions_served") or []),
            "services": list(tenant_profile_context.get("selected_services") or []),
            "business_goals": list(tenant_profile_context.get("business_goals") or []),
            "delivery_model": msp_profile.get("delivery_model"),
        },
        "caller": {
            "name": caller_display_name,
            "display_name_fallback": "your account manager",
            "email": caller_email,
            "role": caller_role,
        },
        "account_context": {
            "m365": m365,
            "service": {
                "open_ticket_count": tickets,
                "open_tickets": [
                    {
                        "subject": row.subject,
                        "status": row.status,
                        "external_ref": row.external_ref,
                    }
                    for row in open_ticket_rows[:6]
                ],
                "recommendation_summaries": rec_summaries,
            },
            "commercial": {
                "open_opportunity_count": opps,
                "open_quote_count": quotes,
                "open_opportunities": [o.model_dump(mode="json") for o in opp_rows[:6]],
                "quotes": [q.model_dump(mode="json") for q in quote_rows[:6]],
            },
            "risk": {
                "risk_score": score.risk_score if score else None,
                "attention_score": score.attention_score if score else None,
                "risk_engine": {
                    "risk_level": risk.risk_level if risk else None,
                    "attention_level": risk.attention_level if risk else None,
                    "confidence_level": risk.confidence_level if risk else None,
                    "reason_codes": risk.reason_codes if risk else [],
                    "coverage_notes": risk.coverage_notes if risk else [],
                },
            },
        },
        "missing_data_notes": missing_data_notes,
    }
    return {
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "status": customer.status,
            "owner_name": customer.owner_name,
            "external_ref": customer.external_ref,
            "demo_profile": customer.demo_profile,
            "finance_panel": fin,
            "m365_panel": m365,
            "risk_engine": {
                "risk_score": risk.risk_score,
                "attention_score": risk.attention_score,
                "risk_level": risk.risk_level,
                "attention_level": risk.attention_level,
                "confidence_level": risk.confidence_level,
                "reason_codes": risk.reason_codes or [],
                "factors": risk.factors_json or [],
                "coverage_notes": risk.coverage_notes or [],
                "scoring_version": risk.scoring_version,
                "calculated_at": risk.calculated_at.isoformat() if risk.calculated_at else None,
            }
            if risk
            else None,
        },
        "scores": {
            "risk_score": score.risk_score if score else None,
            "attention_score": score.attention_score if score else None,
            "growth_score": score.growth_score if score else None,
        },
        "open_counts": {"open_tickets": tickets, "open_opportunities": opps, "open_quotes": quotes},
        "contacts": [
            {
                "id": str(row.id),
                "name": row.name,
                "email": row.email,
                "external_ref": row.external_ref,
            }
            for row in contacts
        ],
        "open_tickets": [
            {
                "id": str(row.id),
                "status": row.status,
                "subject": row.subject,
                "external_ref": row.external_ref,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in open_ticket_rows
        ],
        "recommendation_summaries": rec_summaries,
        "recent_actions": actions,
        "open_recommendations": [r.model_dump(mode="json") for r in rec_rows],
        "open_opportunities": [o.model_dump(mode="json") for o in opp_rows],
        "quotes": [q.model_dump(mode="json") for q in quote_rows],
        "tenant_profile_context": tenant_profile_context,
        "script_context": script_context,
        "missing_data_notes": missing_data_notes,
    }


def build_account_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "account_summary", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_risk_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "risk_summary", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_churn_explanation_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "churn_explanation", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_customer_review_agenda_variables(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    caller_name: str | None = None,
    caller_email: str | None = None,
    caller_role: str | None = None,
) -> dict:
    return {
        "task": "customer_review_agenda",
        **_customer_ai_context_variables(
            db,
            tenant_id,
            customer_id,
            caller_name=caller_name,
            caller_email=caller_email,
            caller_role=caller_role,
        ),
    }


def build_account_manager_next_conversation_variables(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    caller_name: str | None = None,
    caller_email: str | None = None,
    caller_role: str | None = None,
) -> dict:
    return {
        "task": "account_manager_next_conversation",
        **_customer_ai_context_variables(
            db,
            tenant_id,
            customer_id,
            caller_name=caller_name,
            caller_email=caller_email,
            caller_role=caller_role,
        ),
    }


def build_account_manager_call_script_variables(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    caller_name: str | None = None,
    caller_email: str | None = None,
    caller_role: str | None = None,
) -> dict:
    return {
        "task": "account_manager_call_script",
        **_customer_ai_context_variables(
            db,
            tenant_id,
            customer_id,
            caller_name=caller_name,
            caller_email=caller_email,
            caller_role=caller_role,
        ),
    }


def build_billing_variance_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "billing_variance_summary", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_revenue_leakage_explanation_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "revenue_leakage_explanation", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_billing_remediation_next_action_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "billing_remediation_next_action", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_underbilling_opportunity_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "underbilling_opportunity", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_account_confidence_explanation_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "account_confidence_explanation", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_m365_hygiene_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "m365_hygiene_summary", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_m365_upsell_opportunity_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "m365_upsell_opportunity", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_technical_gap_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "technical_gap_summary", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def _latest_m365_connection_and_run(db: Session, tenant_id: UUID) -> tuple[SourceSystemConnection | None, IntegrationSyncRun | None]:
    connection = db.scalars(
        select(SourceSystemConnection)
        .where(SourceSystemConnection.tenant_id == tenant_id, SourceSystemConnection.system_type == "microsoft_365")
        .order_by(SourceSystemConnection.created_at.desc())
    ).first()
    if not connection:
        return None, None
    run = db.scalars(
        select(IntegrationSyncRun)
        .where(IntegrationSyncRun.tenant_id == tenant_id, IntegrationSyncRun.source_connection_id == connection.id)
        .order_by(IntegrationSyncRun.created_at.desc())
    ).first()
    return connection, run


def _top_portfolio_findings(customers: list[dict], *, limit: int = 6) -> list[dict]:
    finding_counts: dict[str, int] = {}
    for row in customers:
        findings = list(row.get("hygiene_findings") or []) + list(row.get("optimisation_findings") or [])
        for finding in findings:
            key = str(finding).strip()
            if not key:
                continue
            finding_counts[key] = finding_counts.get(key, 0) + 1
    ranked = sorted(finding_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    out: list[dict] = []
    for title, count in ranked:
        severity = "high" if count >= 6 else ("medium" if count >= 3 else "low")
        out.append({"title": title, "customer_count": count, "severity": severity})
    return out


def _top_customer_outliers(customers: list[dict], *, limit: int = 8) -> list[dict]:
    def _score(row: dict) -> int:
        return int(row.get("inactive_users_30d") or 0) + int(row.get("unused_licences") or 0) + int(row.get("shared_mailbox_count") or 0)

    ranked = sorted(customers, key=lambda row: (-_score(row), str(row.get("customer_name") or "")))[:limit]
    out: list[dict] = []
    for row in ranked:
        out.append(
            {
                "customer_id": str(row.get("customer_id")) if row.get("customer_id") is not None else None,
                "customer_name": row.get("customer_name"),
                "confidence_level": row.get("confidence_level"),
                "inactive_users_30d": row.get("inactive_users_30d"),
                "unused_licences": row.get("unused_licences"),
                "shared_mailbox_count": row.get("shared_mailbox_count"),
                "stale_users_90d": row.get("stale_users_90d"),
                "disabled_users": row.get("disabled_users"),
                "billing_impact_signals": list(row.get("billing_impact_signals") or []),
                "hygiene_findings": list(row.get("hygiene_findings") or []),
                "optimisation_findings": list(row.get("optimisation_findings") or []),
                "portfolio_rank_reason": "High inactive users / unused licences / shared mailbox concentration.",
            }
        )
    return out


def _m365_portfolio_scope_context(db: Session, tenant_id: UUID) -> dict:
    m365 = M365HealthService(db).build_workspace(tenant_id)
    connection, last_run = _latest_m365_connection_and_run(db, tenant_id)
    reviewable_statuses = {"pending", "unlinked"}
    mapping_review_counts: dict[str, int] = {"pending": 0, "unlinked": 0}
    if connection:
        rows = db.scalars(
            select(ConnectorMappingReview).where(
                ConnectorMappingReview.tenant_id == tenant_id,
                ConnectorMappingReview.source_connection_id == connection.id,
            )
        ).all()
        for row in rows:
            if row.status in reviewable_statuses:
                mapping_review_counts[row.status] = mapping_review_counts.get(row.status, 0) + 1
    customers = list(m365.get("customers", []))
    top_findings = _top_portfolio_findings(customers)
    outliers = _top_customer_outliers(customers)
    summary = dict(m365.get("summary") or {})
    tenant_profile_context = build_tenant_ai_context(db, tenant_id).model_dump(mode="json")
    msp_profile = dict(tenant_profile_context.get("msp_profile_summary") or {})
    msp_name = msp_profile.get("brand_name") or msp_profile.get("legal_name") or "MSP tenant"
    base_url = str(connection.base_url or "") if connection else ""
    connector_mode = "connector_lab_or_dev" if ("connector-lab" in base_url or "localhost" in base_url) else "connector_or_live"
    confidence_notes = list(m365.get("coverage_notes", []))
    if connector_mode == "connector_lab_or_dev":
        confidence_notes.append(
            "Source mode indicates Connector Lab/dev telemetry. Recommendations are directional and should be validated before customer-facing decisions."
        )
    return {
        "analysis_scope": "portfolio_m365_workspace",
        "scope_rules": {
            "portfolio_totals_are_not_single_customer_values": True,
            "customer_examples_must_only_use_top_customer_outliers": True,
            "do_not_invent_missing_security_or_compliance_facts": True,
        },
        "msp_context": {
            "msp_display_name": msp_name,
            "tenant_profile_summary": msp_profile,
            "selected_services": list(tenant_profile_context.get("selected_services") or []),
            "business_goals": list(tenant_profile_context.get("business_goals") or []),
            "vertical_focus": list(tenant_profile_context.get("vertical_focus") or []),
            "regions_served": list(tenant_profile_context.get("regions_served") or []),
        },
        "source_context": {
            "source_family": "microsoft_365",
            "source_mode": connector_mode,
            "connector_status": {
                "configured": connection is not None,
                "connection_id": str(connection.id) if connection else None,
                "health_status": connection.health_status if connection else "not_configured",
                "lifecycle_state": connection.lifecycle_state if connection else "not_configured",
                "last_sync_status": getattr(last_run, "status", None),
                "last_sync_started_at": getattr(last_run, "started_at", None).isoformat()
                if getattr(last_run, "started_at", None)
                else None,
                "last_sync_completed_at": getattr(last_run, "completed_at", None).isoformat()
                if getattr(last_run, "completed_at", None)
                else None,
            },
            "mapping_review": {
                "pending_count": mapping_review_counts.get("pending", 0),
                "unlinked_count": mapping_review_counts.get("unlinked", 0),
                "reviewable_total": mapping_review_counts.get("pending", 0) + mapping_review_counts.get("unlinked", 0),
            },
        },
        "portfolio_totals": {
            "customer_count": int(summary.get("customer_count") or 0),
            "linked_count": int(summary.get("linked_count") or 0),
            "licensed_users_total": int(summary.get("licensed_users_total") or 0),
            "active_users_total": int(summary.get("active_users_total") or 0),
            "inactive_users_total": int(summary.get("inactive_users_total") or 0),
            "mailbox_total": int(summary.get("mailbox_total") or 0),
            "shared_mailbox_total": int(summary.get("shared_mailbox_total") or 0),
            "stale_users_total": int(summary.get("stale_users_total") or 0),
            "disabled_users_total": int(summary.get("disabled_users_total") or 0),
            "billing_mismatch_candidate_count": int(summary.get("billing_mismatch_candidate_count") or 0),
            "optimisation_candidate_count": int(summary.get("optimisation_candidate_count") or 0),
            "label": "These values are portfolio-level totals across linked customers, not single-customer values.",
        },
        "top_findings": top_findings,
        "top_customer_outliers": outliers,
        "data_confidence_notes": confidence_notes,
        "missing_telemetry_notes": [
            "MFA/security analytics can be partial depending on connector depth and upstream availability.",
            "Mapping-review gaps reduce cross-customer certainty for the portfolio summary.",
        ],
    }


def build_m365_customer_context_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    """Customer-only M365 context (no portfolio totals) for customer-level AI routes."""
    repo = CustomerRepository(db)
    customer = repo.get_customer(tenant_id, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    panel = M365HealthService(db).customer_panel(tenant_id, customer_id)
    tenant_profile_context = build_tenant_ai_context(db, tenant_id).model_dump(mode="json")
    return {
        "analysis_scope": "customer_m365_profile",
        "scope_rules": {
            "customer_only_values": True,
            "portfolio_totals_excluded": True,
        },
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "status": customer.status,
            "owner_name": customer.owner_name,
            "mapping_confidence_status": panel.get("confidence_level"),
            "m365_posture": panel,
        },
        "msp_context": {
            "tenant_profile_summary": dict(tenant_profile_context.get("msp_profile_summary") or {}),
            "selected_services": list(tenant_profile_context.get("selected_services") or []),
        },
    }


def build_m365_workspace_summary_variables(db: Session, tenant_id: UUID) -> dict:
    return {
        "task": "m365_hygiene_summary",
        "portfolio_context": _m365_portfolio_scope_context(db, tenant_id),
    }


def build_m365_workspace_opportunity_variables(db: Session, tenant_id: UUID) -> dict:
    return {
        "task": "m365_upsell_opportunity",
        "portfolio_context": _m365_portfolio_scope_context(db, tenant_id),
    }


def build_recommendation_explanation_variables(db: Session, tenant_id: UUID, recommendation_id: UUID) -> dict:
    wrepo = WorkspaceRepository(db)
    rec = wrepo.get_recommendation(tenant_id, recommendation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    cust_name, owner = None, None
    if rec.customer_id:
        c = CustomerRepository(db).get_customer(tenant_id, rec.customer_id)
        if c:
            cust_name, owner = c.name, c.owner_name
    tenant_profile_context = build_tenant_ai_context(db, tenant_id).model_dump(mode="json")
    return {
        "task": "recommendation_explanation",
        "recommendation": {
            "id": str(rec.id),
            "scope": rec.scope,
            "status": rec.status,
            "summary": rec.summary,
            "customer_id": str(rec.customer_id) if rec.customer_id else None,
            "customer_name": cust_name,
            "owner_name": owner,
        },
        "tenant_profile_context": tenant_profile_context,
    }
