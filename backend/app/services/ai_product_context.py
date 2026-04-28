"""Structured variables for product AI tasks (JSON-serializable)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.customers import CustomerRepository
from app.repositories.workspace import WorkspaceRepository
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.m365_health_service import M365HealthService
from app.services.risk_engine_v1 import RiskEngineV1Service
from app.services.tenant_profile import build_tenant_ai_context
from app.services.workspace import WorkspaceService


def _customer_ai_context_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    repo = CustomerRepository(db)
    customer = repo.get_customer(tenant_id, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    score = repo.latest_score(tenant_id, customer_id)
    tickets, opps, quotes = repo.open_counts(tenant_id, customer_id)
    rec_summaries = repo.recommendation_summary(tenant_id, customer_id)
    actions = repo.recent_actions(tenant_id, customer_id)
    ws = WorkspaceService(db)
    rec_rows, opp_rows, quote_rows = ws.customer_workspace_slices(tenant_id, customer_id)
    fin = BillingIntegrityService(db).customer_finance_panel(tenant_id, customer_id)
    m365 = M365HealthService(db).customer_panel(tenant_id, customer_id)
    risk = RiskEngineV1Service(db).latest_score_for_customer(tenant_id, customer_id)
    if fin.get("error") == "not_found":
        fin = {}
    tenant_profile_context = build_tenant_ai_context(db, tenant_id).model_dump(mode="json")
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
        "recommendation_summaries": rec_summaries,
        "recent_actions": actions,
        "open_recommendations": [r.model_dump(mode="json") for r in rec_rows],
        "open_opportunities": [o.model_dump(mode="json") for o in opp_rows],
        "quotes": [q.model_dump(mode="json") for q in quote_rows],
        "tenant_profile_context": tenant_profile_context,
    }


def build_account_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "account_summary", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_risk_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "risk_summary", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_churn_explanation_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "churn_explanation", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_customer_review_agenda_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "customer_review_agenda", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_account_manager_next_conversation_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "account_manager_next_conversation", **_customer_ai_context_variables(db, tenant_id, customer_id)}


def build_account_manager_call_script_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    return {"task": "account_manager_call_script", **_customer_ai_context_variables(db, tenant_id, customer_id)}


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
