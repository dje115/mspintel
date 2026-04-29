from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import AIProvider, TenantAiSettings, TenantAiTaskRoute


class TenantAiConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_settings(self, tenant_id: uuid.UUID) -> TenantAiSettings | None:
        return self.db.get(TenantAiSettings, tenant_id)

    def upsert_settings(self, row: TenantAiSettings) -> TenantAiSettings:
        existing = self.db.get(TenantAiSettings, row.tenant_id)
        if existing:
            existing.default_ai_provider_id = row.default_ai_provider_id
            existing.default_model = row.default_model
            existing.fallback_ai_provider_id = row.fallback_ai_provider_id
            existing.fallback_model = row.fallback_model
            existing.extra = row.extra
            existing.updated_by_user_id = row.updated_by_user_id
            self.db.flush()
            return existing
        self.db.add(row)
        self.db.flush()
        return row

    def list_task_routes(self, tenant_id: uuid.UUID) -> Sequence[TenantAiTaskRoute]:
        stmt = select(TenantAiTaskRoute).where(TenantAiTaskRoute.tenant_id == tenant_id).order_by(TenantAiTaskRoute.task_type)
        return self.db.scalars(stmt).all()

    def get_route_by_task(self, tenant_id: uuid.UUID, task_type: str) -> TenantAiTaskRoute | None:
        stmt = select(TenantAiTaskRoute).where(
            TenantAiTaskRoute.tenant_id == tenant_id, TenantAiTaskRoute.task_type == task_type
        )
        return self.db.scalars(stmt).first()

    def ensure_task_route_stub(self, tenant_id: uuid.UUID, task_type: str, *, prompt_key: str | None = None) -> None:
        """Insert a default enabled route row if missing (same defaults as tenant AI settings list_routes).

        Does not overwrite an existing row. Uses a savepoint so a unique-constraint race only rolls back the insert.
        """
        if self.get_route_by_task(tenant_id, task_type):
            return
        pk = prompt_key or f"{task_type}.system"
        row = TenantAiTaskRoute(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            task_type=task_type,
            ai_provider_id=None,
            model=None,
            fallback_ai_provider_id=None,
            fallback_model=None,
            prompt_key=pk,
            enabled=True,
        )
        try:
            with self.db.begin_nested():
                self.db.add(row)
                self.db.flush()
        except IntegrityError:
            pass

    def list_ai_providers(self, tenant_id: uuid.UUID) -> Sequence[AIProvider]:
        stmt = select(AIProvider).where(AIProvider.tenant_id == tenant_id).order_by(AIProvider.provider_name)
        return self.db.scalars(stmt).all()

    def get_ai_provider(self, tenant_id: uuid.UUID, provider_id: uuid.UUID) -> AIProvider | None:
        stmt = select(AIProvider).where(AIProvider.tenant_id == tenant_id, AIProvider.id == provider_id)
        return self.db.scalars(stmt).first()

    def upsert_route(self, row: TenantAiTaskRoute) -> TenantAiTaskRoute:
        existing = self.get_route_by_task(row.tenant_id, row.task_type)
        if existing:
            existing.ai_provider_id = row.ai_provider_id
            existing.model = row.model
            existing.fallback_ai_provider_id = row.fallback_ai_provider_id
            existing.fallback_model = row.fallback_model
            existing.prompt_key = row.prompt_key
            existing.enabled = row.enabled
            self.db.flush()
            return existing
        self.db.add(row)
        self.db.flush()
        return row
