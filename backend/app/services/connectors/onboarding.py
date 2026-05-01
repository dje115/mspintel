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
CUSTOMER_LIKE_ENTITY_TYPES = {ENTITY_CUSTOMER, "account", "tenant", "organization"}


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


@dataclass
class CustomerCreateEligibility:
    eligible: bool
    blockers: list[str]


@dataclass
class CreateCustomersResult:
    requested_rows: int
    eligible_rows: int
    created_customers: int
    accepted_rows: int
    skipped_rows: int
    created_customer_ids: list[UUID]
    updated_review_ids: list[UUID]


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
                score += 0.9
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
        is_new = row is None
        if is_new:
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
        # Do not rotate operator decisions on every sync — re-opening accepted/remapped/rejected
        # rows caused apparent cross-connector conflicts and lost trust in mapping review.
        if is_new:
            row.status = "pending" if suggestion.customer_id else "unlinked"
        elif row.status in ("accepted", "remapped", "rejected"):
            pass
        else:
            # pending or unlinked: refresh match state from latest customer baseline
            row.status = "pending" if suggestion.customer_id else "unlinked"
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

    def customer_create_eligibility(
        self,
        *,
        row: ConnectorMappingReview,
        tenant_name_keys: set[str],
        tenant_contact_domains: set[str],
    ) -> CustomerCreateEligibility:
        blockers: list[str] = []
        if row.entity_type not in CUSTOMER_LIKE_ENTITY_TYPES:
            blockers.append("unsupported_entity_type")
        if not (row.source_display_name or "").strip():
            blockers.append("missing_source_display_name")
        if row.status not in {"pending", "unlinked"}:
            blockers.append("status_not_importable")
        if row.mapped_customer_id is not None:
            blockers.append("already_mapped")
        normalized_name = _norm_name(row.source_display_name)
        if normalized_name and normalized_name in tenant_name_keys:
            blockers.append("duplicate_normalized_name")
        source_domain = (row.source_domain or "").strip().lower()
        if source_domain and source_domain in tenant_contact_domains:
            blockers.append("duplicate_domain_signal")
        return CustomerCreateEligibility(eligible=not blockers, blockers=blockers)

    def create_customers_from_mapping_reviews(
        self,
        *,
        tenant_id: UUID,
        actor_user_id: UUID | None,
        review_ids: list[UUID] | None = None,
        connection_id: UUID | None = None,
    ) -> CreateCustomersResult:
        stmt = select(ConnectorMappingReview).where(ConnectorMappingReview.tenant_id == tenant_id)
        if review_ids:
            stmt = stmt.where(ConnectorMappingReview.id.in_(review_ids))
        if connection_id:
            stmt = stmt.where(ConnectorMappingReview.source_connection_id == connection_id)
        rows = list(self.db.scalars(stmt.order_by(ConnectorMappingReview.created_at.asc())).all())
        requested_rows = len(rows)
        if requested_rows == 0:
            return CreateCustomersResult(
                requested_rows=0,
                eligible_rows=0,
                created_customers=0,
                accepted_rows=0,
                skipped_rows=0,
                created_customer_ids=[],
                updated_review_ids=[],
            )

        tenant_customers = list(self.db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all())
        tenant_name_keys = {_norm_name(c.name) for c in tenant_customers if c.name}
        tenant_contact_domains: set[str] = set()
        contact_emails = self.db.scalars(select(Contact.email).where(Contact.tenant_id == tenant_id)).all()
        for email in contact_emails:
            if email and "@" in email:
                tenant_contact_domains.add(email.rsplit("@", 1)[1].strip().lower())

        now = datetime.now(UTC)
        eligible_rows = 0
        created_customers = 0
        accepted_rows = 0
        skipped_rows = 0
        created_customer_ids: list[UUID] = []
        updated_review_ids: list[UUID] = []
        conn_by_id = {
            c.id: c
            for c in self.db.scalars(
                select(SourceSystemConnection).where(SourceSystemConnection.tenant_id == tenant_id)
            ).all()
        }

        for row in rows:
            eligibility = self.customer_create_eligibility(
                row=row,
                tenant_name_keys=tenant_name_keys,
                tenant_contact_domains=tenant_contact_domains,
            )
            if not eligibility.eligible:
                skipped_rows += 1
                continue
            eligible_rows += 1

            existing_mapping = self.db.scalars(
                select(SourceEntityMapping).where(
                    SourceEntityMapping.tenant_id == tenant_id,
                    SourceEntityMapping.source_connection_id == row.source_connection_id,
                    SourceEntityMapping.entity_type == row.entity_type,
                    SourceEntityMapping.source_id == row.source_external_id,
                )
            ).first()
            target_customer_id: UUID | None = None
            if existing_mapping:
                target_customer_id = existing_mapping.canonical_entity_id
            else:
                clean_name = (row.source_display_name or "").strip()[:180]
                connection = conn_by_id.get(row.source_connection_id)
                external_prefix = connection.system_type if connection else "connector"
                created = Customer(
                    tenant_id=tenant_id,
                    name=clean_name,
                    status="active",
                    owner_name=None,
                    external_ref=f"{external_prefix}:{row.source_external_id}"[:180],
                )
                self.db.add(created)
                self.db.flush()
                created_customers += 1
                created_customer_ids.append(created.id)
                target_customer_id = created.id
                tenant_name_keys.add(_norm_name(clean_name))
                if row.source_domain:
                    tenant_contact_domains.add(row.source_domain.strip().lower())

                self.audit(
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    event_type="connector_mapping_customer_created",
                    details=f"review_id={row.id}; customer_id={created.id}; source_external_id={row.source_external_id}",
                )

            if not existing_mapping:
                self.db.add(
                    SourceEntityMapping(
                        tenant_id=tenant_id,
                        source_connection_id=row.source_connection_id,
                        entity_type=row.entity_type,
                        source_id=row.source_external_id,
                        canonical_entity_id=target_customer_id,
                        source_updated_at=now,
                        mapping_metadata={"manual_override": True, "action": "create_customer_from_mapping_review"},
                    )
                )
            else:
                existing_mapping.canonical_entity_id = target_customer_id
                existing_mapping.source_updated_at = now
                existing_mapping.mapping_metadata = {
                    "manual_override": True,
                    "action": "create_customer_from_mapping_review",
                }

            row.mapped_customer_id = target_customer_id
            row.status = "accepted"
            row.reviewed_at = now
            row.reviewed_by_user_id = actor_user_id
            row.notes = "customer_created_from_mapping_review"
            accepted_rows += 1
            updated_review_ids.append(row.id)

        if updated_review_ids:
            self.audit(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                event_type="connector_mapping_customers_imported",
                details=(
                    f"requested={requested_rows}; eligible={eligible_rows}; created={created_customers}; "
                    f"accepted={accepted_rows}; skipped={skipped_rows}"
                ),
            )
        self.db.flush()
        return CreateCustomersResult(
            requested_rows=requested_rows,
            eligible_rows=eligible_rows,
            created_customers=created_customers,
            accepted_rows=accepted_rows,
            skipped_rows=skipped_rows,
            created_customer_ids=created_customer_ids,
            updated_review_ids=updated_review_ids,
        )

