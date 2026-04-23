import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.entities import AuditEvent


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(self, *, tenant_id, actor_user_id, event_type: str, details: dict | None = None) -> None:
        event = AuditEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            details=json.dumps(details or {}),
        )
        self.db.add(event)
