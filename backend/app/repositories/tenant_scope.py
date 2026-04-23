from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select


def tenant_scoped(stmt: Select, model, tenant_id: UUID) -> Select:
    return stmt.where(model.tenant_id == tenant_id)


def active_now(ts: datetime | None) -> bool:
    return ts is None or ts > datetime.now(UTC)
