from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AITaskRun


class AITaskRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def latest_for(
        self,
        tenant_id: uuid.UUID,
        task_type: str,
        *,
        customer_id: uuid.UUID | None = None,
        recommendation_id: uuid.UUID | None = None,
    ) -> AITaskRun | None:
        stmt = select(AITaskRun).where(AITaskRun.tenant_id == tenant_id, AITaskRun.task_type == task_type)
        if customer_id:
            stmt = stmt.where(AITaskRun.customer_id == customer_id)
        if recommendation_id:
            stmt = stmt.where(AITaskRun.recommendation_id == recommendation_id)
        stmt = stmt.order_by(AITaskRun.created_at.desc()).limit(1)
        return self.db.scalars(stmt).first()

    def list_recent_platform(self, limit: int = 100) -> Sequence[AITaskRun]:
        stmt = select(AITaskRun).order_by(AITaskRun.created_at.desc()).limit(limit)
        return self.db.scalars(stmt).all()
