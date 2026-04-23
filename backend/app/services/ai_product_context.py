"""Structured variables for product AI tasks (JSON-serializable)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.customers import CustomerRepository
from app.repositories.workspace import WorkspaceRepository
from app.services.workspace import WorkspaceService


def build_account_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
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
    return {
        "task": "account_summary",
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "status": customer.status,
            "owner_name": customer.owner_name,
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
    }


def build_risk_summary_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    base = build_account_summary_variables(db, tenant_id, customer_id)
    base["task"] = "risk_summary"
    return base


def build_churn_explanation_variables(db: Session, tenant_id: UUID, customer_id: UUID) -> dict:
    base = build_account_summary_variables(db, tenant_id, customer_id)
    base["task"] = "churn_explanation"
    return base


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
    }
