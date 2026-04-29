from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AuditEvent,
    ConnectorMappingReview,
    Contact,
    Customer,
    IntegrationSyncRun,
    SourceEntityMapping,
    SourceSystemConnection,
)
from app.services.connectors.constants import ENTITY_CUSTOMER


LIFECYCLE_STATES = {"configured", "tested", "active", "disabled", "paused", "error"}
SYNC_BEHAVIORS = {"manual_sync_only", "scheduled_sync_enabled"}
MAPPING_ACTIONS = {"accept", "reject", "remap", "unlink"}
MAPPING_STATUSES = {"pending", "accepted", "rejected", "remapped", "unlinked"}


def _norm_name(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())


@dataclass
class MatchSuggestion:
    customer_id: UUID | None
    confidence: str
    score: float
    reasons: list[str]


class ConnectorOnboardingService:
    def __init__(self, db: Session):
        self.db = db

    def audit(self, *, tenant_id: UUID, actor_user_id: UUID | None, event_type: str, details: str) -> None:
        self.db.add(AuditEvent(tenant_id=tenant_id, actor_user_id=actor_user_id, event_type=event_type, details=details))

    def suggest_customer(self, *, tenant_id: UUID, source_name: str | None, source_domain: str | None) -> MatchSuggestion:
        customers = list(self.db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all())
        if not customers:
            return MatchSuggestion(None, "low", 0.0, ["no_tenant_customers"])

        norm_target = _norm_name(source_name)
        best: tuple[Customer | None, float, list[str]] = (None, 0.0, [])
        for c in customers:
            score = 0.0
            reasons: list[str] = []
            norm_customer = _norm_name(c.name)
            if norm_target and norm_target == norm_customer:
                score += 0.75
                reasons.append("exact_normalized_name")
            elif norm_target and (norm_target in norm_customer or norm_customer in norm_target):
                score += 0.55
                reasons.append("near_name_match")

            if source_domain:
                domain = source_domain.lower()
                customer_domain = getattr(c, "domain", None)
                if customer_domain and str(customer_domain).lower() == domain:
                    score += 0.3
                    reasons.append("customer_domain_match")
                email_match = self.db.scalar(
                    select(func.count()).select_from(
                        select(Contact.id)
                        .where(
                            Contact.tenant_id == tenant_id,
                            Contact.customer_id == c.id,
                            Contact.email.ilike(f"%@{domain}"),
                        )
                        .subquery()
                    )
                )
                if int(email_match or 0) > 0:
                    score += 0.25
                    reasons.append("contact_email_domain_match")
            if score > best[1]:
                best = (c, score, reasons)

        winner, score, reasons = best
        if not winner:
            return MatchSuggestion(None, "low", 0.0, ["no_match"])
        if score >= 0.9:
            return MatchSuggestion(winner.id, "high", score, reasons or ["high_confidence_rule"])
        if score >= 0.55:
            return MatchSuggestion(winner.id, "medium", score, reasons or ["review_needed"])
        return MatchSuggestion(None, "low", score, reasons or ["low_signal"])

    def upsert_mapping_review_candidate(
        self,
        *,
        tenant_id: UUID,
        source_connection_id: UUID,
        entity_type: str,
        source_external_id: str,
        source_display_name: str | None,
        source_domain: str | None = None,
    ) -> ConnectorMappingReview:
        suggestion = self.suggest_customer(tenant_id=tenant_id, source_name=source_display_name, source_domain=source_domain)
        row = self.db.scalars(
            select(ConnectorMappingReview).where(
                ConnectorMappingReview.tenant_id == tenant_id,
                ConnectorMappingReview.source_connection_id == source_connection_id,
                ConnectorMappingReview.entity_type == entity_type,
                ConnectorMappingReview.source_external_id == source_external_id,
            )
        ).first()
        if not row:
            row = ConnectorMappingReview(
                tenant_id=tenant_id,
                source_connection_id=source_connection_id,
                entity_type=entity_type,
                source_external_id=source_external_id,
            )
            self.db.add(row)
        row.source_display_name = source_display_name
        row.source_domain = source_domain
        row.suggested_customer_id = suggestion.customer_id
        row.suggested_confidence = suggestion.confidence
        row.suggested_score = Decimal(str(round(suggestion.score, 2)))
        row.suggested_reasons = suggestion.reasons
        row.status = "pending"
        return row

    def list_mapping_reviews(
        self,
        tenant_id: UUID,
        connection_id: UUID | None = None,
        statuses: set[str] | None = None,
        confidence_labels: set[str] | None = None,
        search: str | None = None,
        customer_id: UUID | None = None,
    ) -> list[ConnectorMappingReview]:
        stmt = select(ConnectorMappingReview).where(ConnectorMappingReview.tenant_id == tenant_id)
        if connection_id:
            stmt = stmt.where(ConnectorMappingReview.source_connection_id == connection_id)
        if statuses:
            stmt = stmt.where(ConnectorMappingReview.status.in_(statuses))
        if confidence_labels:
            stmt = stmt.where(ConnectorMappingReview.suggested_confidence.in_(confidence_labels))
        if customer_id:
            stmt = stmt.where(
                (ConnectorMappingReview.mapped_customer_id == customer_id)
                | (ConnectorMappingReview.suggested_customer_id == customer_id)
            )
        if search:
            like_q = f"%{search.strip()}%"
            stmt = stmt.where(
                (ConnectorMappingReview.source_display_name.ilike(like_q))
                | (ConnectorMappingReview.source_external_id.ilike(like_q))
                | (ConnectorMappingReview.source_domain.ilike(like_q))
            )
        return list(self.db.scalars(stmt.order_by(ConnectorMappingReview.updated_at.desc())).all())

    def apply_mapping_action(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        review_id: UUID,
        action: str,
        customer_id: UUID | None,
        notes: str | None,
    ) -> ConnectorMappingReview:
        if action not in MAPPING_ACTIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported mapping action")
        row = self.db.get(ConnectorMappingReview, review_id)
        if not row or row.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping review not found")
        target_customer_id = customer_id or row.suggested_customer_id
        now = datetime.now(UTC)

        if action in {"accept", "remap"}:
            if not target_customer_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer_id is required for accept/remap")
            target_customer = self.db.scalars(
                select(Customer).where(Customer.tenant_id == tenant_id, Customer.id == target_customer_id)
            ).first()
            if not target_customer:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target customer not found")
            mapping = self.db.scalars(
                select(SourceEntityMapping).where(
                    SourceEntityMapping.tenant_id == tenant_id,
                    SourceEntityMapping.source_connection_id == row.source_connection_id,
                    SourceEntityMapping.entity_type == row.entity_type,
                    SourceEntityMapping.source_id == row.source_external_id,
                )
            ).first()
            if not mapping:
                mapping = SourceEntityMapping(
                    tenant_id=tenant_id,
                    source_connection_id=row.source_connection_id,
                    entity_type=row.entity_type,
                    source_id=row.source_external_id,
                    canonical_entity_id=target_customer_id,
                    source_updated_at=now,
                    mapping_metadata={"manual_override": True, "action": action},
                )
                self.db.add(mapping)
            else:
                mapping.canonical_entity_id = target_customer_id
                mapping.source_updated_at = now
                mapping.mapping_metadata = {"manual_override": True, "action": action}
            row.mapped_customer_id = target_customer_id
            row.status = "accepted" if action == "accept" else "remapped"
        elif action == "unlink":
            mapping = self.db.scalars(
                select(SourceEntityMapping).where(
                    SourceEntityMapping.tenant_id == tenant_id,
                    SourceEntityMapping.source_connection_id == row.source_connection_id,
                    SourceEntityMapping.entity_type == row.entity_type,
                    SourceEntityMapping.source_id == row.source_external_id,
                )
            ).first()
            if mapping:
                self.db.delete(mapping)
            row.mapped_customer_id = None
            row.status = "unlinked"
        else:
            row.status = "rejected"

        row.reviewed_at = now
        row.reviewed_by_user_id = actor_user_id
        row.notes = notes
        self.audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type=f"connector_mapping_{action}",
            details=f"review_id={row.id}; connection_id={row.source_connection_id}; external_id={row.source_external_id}",
        )
        self.db.flush()
        return row

    def latest_sync_runs_by_connection(self, tenant_id: UUID, connection_ids: set[UUID]) -> dict[UUID, IntegrationSyncRun]:
        if not connection_ids:
            return {}
        rows = self.db.scalars(
            select(IntegrationSyncRun)
            .where(
                IntegrationSyncRun.tenant_id == tenant_id,
                IntegrationSyncRun.source_connection_id.in_(connection_ids),
            )
            .order_by(IntegrationSyncRun.started_at.desc().nullslast(), IntegrationSyncRun.created_at.desc())
        ).all()
        latest: dict[UUID, IntegrationSyncRun] = {}
        for row in rows:
            if row.source_connection_id not in latest:
                latest[row.source_connection_id] = row
        return latest

