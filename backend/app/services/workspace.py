from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer
from app.repositories.workspace import (
    WorkspaceRepository,
    _next_action_for_rec,
    _priority_for_scope,
)
from app.schemas.workspace import (
    CommercialHubResponse,
    OpportunityRow,
    QuoteRow,
    RecommendationListResponse,
    RecommendationRow,
    RiskQueueResponse,
    RiskQueueRow,
    RiskRecomputeResponse,
    ServiceRiskResponse,
    ServiceRiskSection,
)
from app.services.risk_engine_v1 import RISK_ENGINE_VERSION, RiskEngineV1Service


def _row_to_recommendation_row(rec, cname: str | None, owner: str | None) -> RecommendationRow:
    return RecommendationRow(
        id=rec.id,
        customer_id=rec.customer_id,
        customer_name=cname,
        owner_name=owner,
        scope=rec.scope,
        status=rec.status,
        summary=rec.summary,
        category=rec.scope,
        priority=_priority_for_scope(rec.scope),
        suggested_next_action=_next_action_for_rec(rec.scope, rec.summary),
        created_at=rec.created_at,
    )


class WorkspaceService:
    def __init__(self, db: Session):
        self.repo = WorkspaceRepository(db)

    def list_recommendations(
        self,
        tenant_id: UUID,
        *,
        status: str | None,
        scope: str | None,
        customer_id: UUID | None,
        owner_search: str | None,
        page: int,
        page_size: int,
    ) -> RecommendationListResponse:
        rows, total = self.repo.list_recommendations(
            tenant_id,
            status=status,
            scope=scope,
            customer_id=customer_id,
            owner_search=owner_search,
            page=page,
            page_size=page_size,
        )
        items = [_row_to_recommendation_row(rec, cname, owner) for rec, cname, owner in rows]
        return RecommendationListResponse(items=items, page=page, page_size=page_size, total=total)

    def patch_recommendation(self, tenant_id: UUID, rec_id: UUID, new_status: str) -> RecommendationRow:
        rec = self.repo.get_recommendation(tenant_id, rec_id)
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
        rec.status = new_status
        self.repo.db.commit()
        self.repo.db.refresh(rec)
        cname, owner = None, None
        if rec.customer_id:
            c = self.repo.db.get(Customer, rec.customer_id)
            if c:
                cname, owner = c.name, c.owner_name
        return _row_to_recommendation_row(rec, cname, owner)

    def commercial_hub(self, tenant_id: UUID) -> CommercialHubResponse:
        opps: list[OpportunityRow] = []
        for opp, cname in self.repo.list_opportunities(tenant_id):
            label = opp.title or ("Open opportunity" if opp.status == "open" else f"Opportunity ({opp.status})")
            opps.append(
                OpportunityRow(
                    id=opp.id,
                    customer_id=opp.customer_id,
                    customer_name=cname,
                    title=label,
                    status=opp.status,
                    value_cents=opp.value_cents,
                    revisit_reason=None,
                    suggested_next_action="Advance or close in PSA",
                    created_at=opp.created_at,
                )
            )
        lost: list[QuoteRow] = []
        for q, cname in self.repo.list_quotes(tenant_id, statuses=["lost"]):
            lost.append(
                QuoteRow(
                    id=q.id,
                    customer_id=q.customer_id,
                    customer_name=cname,
                    title=q.title or "Lost quote — revisit",
                    status=q.status,
                    value_cents=q.value_cents,
                    revisit_reason="Commercial signal: lost stage",
                    suggested_next_action="Re-engage stakeholder; check pricing fit",
                    created_at=q.created_at,
                )
            )
        open_q: list[QuoteRow] = []
        for q, cname in self.repo.list_quotes(tenant_id, statuses=["open", "draft"]):
            open_q.append(
                QuoteRow(
                    id=q.id,
                    customer_id=q.customer_id,
                    customer_name=cname,
                    title=q.title or ("Active quote" if q.status == "open" else "Draft quote"),
                    status=q.status,
                    value_cents=q.value_cents,
                    revisit_reason=None,
                    suggested_next_action="Move to won or document loss reason",
                    created_at=q.created_at,
                )
            )
        return CommercialHubResponse(opportunities=opps, lost_quotes=lost, open_quotes=open_q)

    def service_risk(self, tenant_id: UUID) -> ServiceRiskResponse:
        open_tickets = self.repo.open_ticket_count(tenant_id)
        at_risk = self.repo.at_risk_customer_count(tenant_id)
        lost = self.repo.lost_quote_count(tenant_id)
        backup = ServiceRiskSection(
            title="Backup coverage & jobs",
            summary="When backup integrations are connected, failed jobs, stale agents, and coverage gaps will rank here.",
            metrics={"placeholder": 1, "lost_quotes_context": lost},
            placeholder=True,
        )
        delivery = ServiceRiskSection(
            title="Service delivery load",
            summary="Open ticket pressure and at-risk accounts indicate where delivery may be stretched.",
            metrics={"open_tickets": open_tickets, "at_risk_accounts": at_risk},
            placeholder=False,
        )
        return ServiceRiskResponse(backup=backup, service_delivery=delivery)

    def customer_workspace_slices(self, tenant_id: UUID, customer_id: UUID) -> tuple[list[RecommendationRow], list[OpportunityRow], list[QuoteRow]]:
        recs, _ = self.repo.list_recommendations(
            tenant_id, status=None, scope=None, customer_id=customer_id, owner_search=None, page=1, page_size=50
        )
        rec_rows = [_row_to_recommendation_row(r, n, o) for r, n, o in recs]
        opp_rows = []
        for opp, cname in self.repo.list_opportunities_for_customer(tenant_id, customer_id):
            opp_rows.append(
                OpportunityRow(
                    id=opp.id,
                    customer_id=opp.customer_id,
                    customer_name=cname,
                    title=opp.title or ("Open opportunity" if opp.status == "open" else f"Opportunity ({opp.status})"),
                    status=opp.status,
                    value_cents=opp.value_cents,
                    revisit_reason=None,
                    suggested_next_action="Advance or close in PSA",
                    created_at=opp.created_at,
                )
            )
        quote_rows = []
        for q, cname in self.repo.list_quotes_for_customer(tenant_id, customer_id):
            quote_rows.append(
                QuoteRow(
                    id=q.id,
                    customer_id=q.customer_id,
                    customer_name=cname,
                    title=q.title or f"Quote ({q.status})",
                    status=q.status,
                    value_cents=q.value_cents,
                    revisit_reason="Lost — revisit" if q.status == "lost" else None,
                    suggested_next_action="Revisit pricing" if q.status == "lost" else "Update stage in PSA",
                    created_at=q.created_at,
                )
            )
        return rec_rows, opp_rows, quote_rows

    def risk_queue(
        self,
        tenant_id: UUID,
        *,
        mode: str,
        search: str | None,
        owner_search: str | None,
        page: int,
        page_size: int,
    ) -> RiskQueueResponse:
        from app.services.risk_engine_v1 import RiskEngineV1Service

        svc = RiskEngineV1Service(self.repo.db)
        score_map = svc.latest_scores_map(tenant_id)
        customers = list(self.repo.db.scalars(select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.name)).all())
        if search:
            q = search.lower()
            customers = [c for c in customers if q in c.name.lower()]
        if owner_search:
            q = owner_search.lower()
            customers = [c for c in customers if (c.owner_name or "").lower().find(q) >= 0]
        rows: list[RiskQueueRow] = []
        for c in customers:
            s = score_map.get(c.id)
            if not s:
                continue
            if mode == "at_risk" and s.risk_score < 45:
                continue
            if mode == "attention" and s.attention_score < 45:
                continue
            factors = s.factors_json or []
            top_reasons = [f.get("title", f.get("code", "")) for f in factors[:3] if isinstance(f, dict)]
            rows.append(
                RiskQueueRow(
                    customer_id=c.id,
                    customer_name=c.name,
                    owner_name=c.owner_name,
                    status=c.status,
                    risk_score=s.risk_score,
                    attention_score=s.attention_score,
                    risk_level=s.risk_level,
                    attention_level=s.attention_level,
                    confidence_level=s.confidence_level,
                    reason_codes=s.reason_codes or [],
                    top_reasons=top_reasons,
                    coverage_notes=s.coverage_notes or [],
                    next_step_placeholder=(
                        "Plan next customer conversation using top risk factors and confirm owner/actions."
                    ),
                    calculated_at=s.calculated_at,
                )
            )
        rows.sort(
            key=(lambda r: (r.risk_score, r.attention_score))
            if mode == "at_risk"
            else (lambda r: (r.attention_score, r.risk_score)),
            reverse=True,
        )
        total = len(rows)
        offset = (page - 1) * page_size
        paged = rows[offset : offset + page_size]
        return RiskQueueResponse(
            mode=mode,
            scoring_version=RISK_ENGINE_VERSION,
            page=page,
            page_size=page_size,
            total=total,
            items=paged,
        )

    def recompute_risk(self, tenant_id: UUID, customer_id: UUID | None) -> RiskRecomputeResponse:
        svc = RiskEngineV1Service(self.repo.db)
        if customer_id:
            svc.recompute_customer(tenant_id, customer_id)
            processed = 1
            mode = "single_customer"
        else:
            res = svc.recompute_tenant(tenant_id)
            processed = int(res["processed"])
            mode = "tenant_batch"
        self.repo.db.flush()
        return RiskRecomputeResponse(mode=mode, processed=processed, scoring_version=RISK_ENGINE_VERSION)
