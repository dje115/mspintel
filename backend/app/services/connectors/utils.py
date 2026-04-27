from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import SourceEntityMapping


def upsert_source_entity_mapping(
    db: Session,
    *,
    tenant_id: UUID,
    source_connection_id: UUID,
    entity_type: str,
    source_id: str,
    canonical_entity_id: UUID,
) -> None:
    stmt = select(SourceEntityMapping).where(
        SourceEntityMapping.tenant_id == tenant_id,
        SourceEntityMapping.source_connection_id == source_connection_id,
        SourceEntityMapping.entity_type == entity_type,
        SourceEntityMapping.source_id == source_id,
    )
    row = db.scalars(stmt).first()
    if row:
        row.canonical_entity_id = canonical_entity_id
        row.source_updated_at = datetime.now(UTC)
        return
    db.add(
        SourceEntityMapping(
            tenant_id=tenant_id,
            source_connection_id=source_connection_id,
            entity_type=entity_type,
            source_id=source_id,
            canonical_entity_id=canonical_entity_id,
            source_updated_at=datetime.now(UTC),
        )
    )

