import json
import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import AuditEvent


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        *,
        tenant_id: UUID | None,
        actor_user_id: UUID | None,
        event_type: str,
        details: dict | None = None,
    ) -> None:
        """Persist an audit row.

        ``tenant_id=None`` denotes a **platform-scoped** event (no synthetic tenant).
        Tenant-owned flows must always pass a real tenant id.
        """
        event = AuditEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            details=json.dumps(details or {}),
        )
        self.db.add(event)
