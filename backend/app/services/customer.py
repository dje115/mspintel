from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import ConnectorMappingReview, Contact, SourceEntityMapping, SourceSystemConnection
from app.repositories.customers import CustomerRepository
from app.schemas.billing_integrity import FinanceCustomerPanel
from app.schemas.customer import CustomerDetailResponse, CustomerListItem, CustomerListResponse
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.m365_health_service import M365HealthService
from app.services.risk_engine_v1 import RiskEngineV1Service
from app.services.workspace import WorkspaceService


class CustomerService:
    def __init__(self, db: Session):
        self.repo = CustomerRepository(db)
        self.workspace = WorkspaceService(db)

    def list_customers(self, tenant_id: UUID, search: str | None, status_filter: str | None, page: int, page_size: int):
        customers, total = self.repo.list_customers(tenant_id, search, status_filter, page, page_size)
        score_map = RiskEngineV1Service(self.repo.db).latest_scores_map(tenant_id)
        items: list[CustomerListItem] = []
        for customer in customers:
            score = score_map.get(customer.id)
            recs = self.repo.recommendation_summary(tenant_id, customer.id)
            items.append(
                CustomerListItem(
                    id=customer.id,
                    name=customer.name,
                    status=customer.status,
                    owner_name=customer.owner_name,
                    risk_score=score.risk_score if score else None,
                    attention_score=score.attention_score if score else None,
                    growth_score=score.growth_score if score else None,
                    next_best_action=recs[0] if recs else None,
                )
            )

        return CustomerListResponse(items=items, page=page, page_size=page_size, total=total)

    def get_customer_detail(self, tenant_id: UUID, customer_id: UUID) -> CustomerDetailResponse:
        customer = self.repo.get_customer(tenant_id, customer_id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

        score = self.repo.latest_score(tenant_id, customer_id)
        tickets, opps, quotes = self.repo.open_counts(tenant_id, customer_id)
        recs = self.repo.recommendation_summary(tenant_id, customer_id)
        actions = self.repo.recent_actions(tenant_id, customer_id)
        rec_rows, opp_rows, quote_rows = self.workspace.customer_workspace_slices(tenant_id, customer_id)
        contacts = list(
            self.repo.db.scalars(
                select(Contact)
                .where(Contact.tenant_id == tenant_id, Contact.customer_id == customer_id)
                .order_by(Contact.name.asc())
                .limit(20)
            ).all()
        )
        risk = RiskEngineV1Service(self.repo.db).latest_score_for_customer(tenant_id, customer_id)

        fin_raw = BillingIntegrityService(self.repo.db).customer_finance_panel(tenant_id, customer_id)
        fin_raw.pop("error", None)
        finance_panel = FinanceCustomerPanel(**fin_raw)
        m365_panel = M365HealthService(self.repo.db).customer_panel(tenant_id, customer_id)
        contributing = list(
            self.repo.db.scalars(
                select(func.distinct(SourceSystemConnection.system_type))
                .join(SourceEntityMapping, SourceEntityMapping.source_connection_id == SourceSystemConnection.id)
                .where(
                    SourceSystemConnection.tenant_id == tenant_id,
                    SourceEntityMapping.tenant_id == tenant_id,
                    SourceEntityMapping.entity_type == "customer",
                    SourceEntityMapping.canonical_entity_id == customer_id,
                )
            ).all()
        )
        connected = list(
            self.repo.db.scalars(select(SourceSystemConnection.system_type).where(SourceSystemConnection.tenant_id == tenant_id)).all()
        )
        unresolved = self.repo.db.scalar(
            select(func.count()).where(
                ConnectorMappingReview.tenant_id == tenant_id,
                ConnectorMappingReview.status == "pending",
                ConnectorMappingReview.suggested_customer_id == customer_id,
            )
        ) or 0
        missing = [s for s in connected if s not in contributing]
        connector_coverage = {
            "connected_systems": contributing,
            "missing_systems": missing,
            "unresolved_mapping_count": int(unresolved),
            "confidence_note": (
                "Cross-system confidence is constrained by unresolved mappings."
                if int(unresolved) > 0
                else "Cross-system linkage is stable for currently connected systems."
            ),
        }

        return CustomerDetailResponse(
            id=customer.id,
            name=customer.name,
            status=customer.status,
            owner_name=customer.owner_name,
            demo_profile=customer.demo_profile,
            finance=finance_panel,
            m365=m365_panel,
            connector_coverage=connector_coverage,
            risk_engine={
                "scoring_version": risk.scoring_version,
                "calculated_at": risk.calculated_at.isoformat() if risk.calculated_at else None,
                "risk_level": risk.risk_level,
                "attention_level": risk.attention_level,
                "confidence_level": risk.confidence_level,
                "reason_codes": risk.reason_codes or [],
                "factors": risk.factors_json or [],
                "coverage_notes": risk.coverage_notes or [],
            }
            if risk
            else None,
            latest_scores={
                "risk_score": score.risk_score,
                "attention_score": score.attention_score,
                "growth_score": score.growth_score,
            }
            if score
            else None,
            open_tickets_count=tickets,
            open_opportunities_count=opps,
            open_quotes_count=quotes,
            recommendation_summary=recs,
            recent_actions=actions,
            contacts=[
                {
                    "id": str(row.id),
                    "name": row.name,
                    "email": row.email,
                    "external_ref": row.external_ref,
                }
                for row in contacts
            ],
            recommendations=rec_rows,
            opportunities=opp_rows,
            quotes=quote_rows,
        )
