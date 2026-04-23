from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.ai_constants import PROMPT_SCOPE_PLATFORM, PROMPT_SCOPE_TENANT
from app.models.entities import PromptActivationEvent, PromptDefinition, PromptVersion


class PromptRegistryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_platform_definition_by_key(self, prompt_key: str) -> PromptDefinition | None:
        stmt = select(PromptDefinition).where(
            PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
            PromptDefinition.tenant_id.is_(None),
            PromptDefinition.prompt_key == prompt_key,
        )
        return self.db.scalars(stmt).first()

    def get_tenant_override_definition(self, tenant_id: uuid.UUID, prompt_key: str) -> PromptDefinition | None:
        stmt = select(PromptDefinition).where(
            PromptDefinition.scope == PROMPT_SCOPE_TENANT,
            PromptDefinition.tenant_id == tenant_id,
            PromptDefinition.prompt_key == prompt_key,
        )
        return self.db.scalars(stmt).first()

    def list_platform_definitions(self) -> Sequence[PromptDefinition]:
        stmt = (
            select(PromptDefinition)
            .where(PromptDefinition.scope == PROMPT_SCOPE_PLATFORM, PromptDefinition.tenant_id.is_(None))
            .order_by(PromptDefinition.prompt_key)
        )
        return self.db.scalars(stmt).all()

    def list_tenant_override_definitions(self, tenant_id: uuid.UUID) -> Sequence[PromptDefinition]:
        stmt = (
            select(PromptDefinition)
            .where(PromptDefinition.scope == PROMPT_SCOPE_TENANT, PromptDefinition.tenant_id == tenant_id)
            .order_by(PromptDefinition.prompt_key)
        )
        return self.db.scalars(stmt).all()

    def get_definition(self, definition_id: uuid.UUID) -> PromptDefinition | None:
        return self.db.get(PromptDefinition, definition_id)

    def add_definition(self, row: PromptDefinition) -> PromptDefinition:
        self.db.add(row)
        self.db.flush()
        return row

    def list_versions(self, prompt_definition_id: uuid.UUID) -> Sequence[PromptVersion]:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_definition_id == prompt_definition_id)
            .order_by(PromptVersion.version_number.desc())
        )
        return self.db.scalars(stmt).all()

    def get_version(self, version_id: uuid.UUID) -> PromptVersion | None:
        return self.db.get(PromptVersion, version_id)

    def max_version_number(self, prompt_definition_id: uuid.UUID) -> int:
        n = self.db.scalar(
            select(func.coalesce(func.max(PromptVersion.version_number), 0)).where(
                PromptVersion.prompt_definition_id == prompt_definition_id
            )
        )
        return int(n or 0)

    def deactivate_all_versions(self, prompt_definition_id: uuid.UUID) -> None:
        for v in self.db.scalars(select(PromptVersion).where(PromptVersion.prompt_definition_id == prompt_definition_id)):
            v.is_active = False

    def add_version(self, row: PromptVersion) -> PromptVersion:
        self.db.add(row)
        self.db.flush()
        return row

    def add_activation_event(self, row: PromptActivationEvent) -> None:
        self.db.add(row)

    def delete_definition_cascade(self, definition: PromptDefinition) -> None:
        self.db.delete(definition)
