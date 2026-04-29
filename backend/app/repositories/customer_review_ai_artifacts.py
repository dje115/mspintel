from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.entities import CustomerReviewAiArtifact


class CustomerReviewAiArtifactRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, tenant_id: uuid.UUID, artifact_id: uuid.UUID) -> CustomerReviewAiArtifact | None:
        row = self.db.get(CustomerReviewAiArtifact, artifact_id)
        if not row or row.tenant_id != tenant_id:
            return None
        return row

    def list_for_customer(
        self,
        tenant_id: uuid.UUID,
        customer_id: uuid.UUID,
        *,
        artifact_type: str | None = None,
        limit: int = 80,
    ) -> Sequence[CustomerReviewAiArtifact]:
        stmt = (
            select(CustomerReviewAiArtifact)
            .where(
                CustomerReviewAiArtifact.tenant_id == tenant_id,
                CustomerReviewAiArtifact.customer_id == customer_id,
            )
            .order_by(CustomerReviewAiArtifact.created_at.desc())
            .limit(limit)
        )
        if artifact_type:
            stmt = stmt.where(CustomerReviewAiArtifact.artifact_type == artifact_type)
        return self.db.scalars(stmt).all()

    def latest_for_type(
        self, tenant_id: uuid.UUID, customer_id: uuid.UUID, artifact_type: str
    ) -> CustomerReviewAiArtifact | None:
        stmt = (
            select(CustomerReviewAiArtifact)
            .where(
                CustomerReviewAiArtifact.tenant_id == tenant_id,
                CustomerReviewAiArtifact.customer_id == customer_id,
                CustomerReviewAiArtifact.artifact_type == artifact_type,
                CustomerReviewAiArtifact.status == "succeeded",
            )
            .order_by(CustomerReviewAiArtifact.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def recent_summaries_for_prompt(
        self,
        tenant_id: uuid.UUID,
        customer_id: uuid.UUID,
        *,
        artifact_types: Sequence[str],
        per_type_limit: int = 3,
        max_items: int = 8,
    ) -> list[dict]:
        """Compact prior short_context payloads for continuity (not raw full outputs)."""
        out: list[dict] = []
        for at in artifact_types:
            rows = (
                self.db.scalars(
                    select(CustomerReviewAiArtifact)
                    .where(
                        CustomerReviewAiArtifact.tenant_id == tenant_id,
                        CustomerReviewAiArtifact.customer_id == customer_id,
                        CustomerReviewAiArtifact.artifact_type == at,
                        CustomerReviewAiArtifact.status == "succeeded",
                    )
                    .order_by(CustomerReviewAiArtifact.created_at.desc())
                    .limit(per_type_limit)
                )
                .all()
            )
            for row in rows:
                sc = row.short_context_json if isinstance(row.short_context_json, dict) else {}
                out.append(
                    {
                        "artifact_type": at,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "summary": sc.get("summary"),
                        "key_points": sc.get("key_points") or [],
                        "recommended_actions": sc.get("recommended_actions") or [],
                        "open_questions": sc.get("open_questions") or [],
                        "customer_safe_topics": sc.get("customer_safe_topics") or [],
                        "internal_only_notes": sc.get("internal_only_notes") or [],
                        "confidence_level": sc.get("confidence_level"),
                        "missing_data": sc.get("missing_data") or [],
                    }
                )
                if len(out) >= max_items:
                    return out
        return out

    def supersede_succeeded_same_type(
        self,
        tenant_id: uuid.UUID,
        customer_id: uuid.UUID,
        artifact_type: str,
        *,
        except_id: uuid.UUID | None = None,
    ) -> None:
        stmt = (
            update(CustomerReviewAiArtifact)
            .where(
                CustomerReviewAiArtifact.tenant_id == tenant_id,
                CustomerReviewAiArtifact.customer_id == customer_id,
                CustomerReviewAiArtifact.artifact_type == artifact_type,
                CustomerReviewAiArtifact.status == "succeeded",
            )
            .values(status="superseded")
        )
        if except_id:
            stmt = stmt.where(CustomerReviewAiArtifact.id != except_id)
        self.db.execute(stmt)

    def add(self, row: CustomerReviewAiArtifact) -> CustomerReviewAiArtifact:
        self.db.add(row)
        self.db.flush()
        return row
