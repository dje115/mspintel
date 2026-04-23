"""Prompt definitions, versions, inheritance (platform vs tenant), activation."""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.ai_constants import PROMPT_SCOPE_PLATFORM, PROMPT_SCOPE_TENANT
from app.models.entities import PromptActivationEvent, PromptDefinition, PromptVersion
from app.repositories.prompt_registry import PromptRegistryRepository
from app.schemas.ai_foundation import (
    PlatformPromptDefinitionCreate,
    PromptCompareResponse,
    PromptDetailResponse,
    PromptListItem,
    PromptVersionCreateBody,
    PromptVersionRow,
)
from app.services.audit import AuditService


def _version_row(v: PromptVersion) -> PromptVersionRow:
    return PromptVersionRow(
        id=v.id,
        version_number=v.version_number,
        change_note=v.change_note,
        is_active=v.is_active,
        created_at=v.created_at,
        created_by_user_id=v.created_by_user_id,
        version_metadata=v.version_metadata,
    )


class PromptApplicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PromptRegistryRepository(db)
        self.audit = AuditService(db)

    def _active_version(self, definition_id: UUID) -> PromptVersion | None:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_definition_id == definition_id, PromptVersion.is_active.is_(True))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def list_prompts_for_tenant(self, tenant_id: UUID) -> list[PromptListItem]:
        platform_defs = self.repo.list_platform_definitions()
        overrides = {d.prompt_key: d for d in self.repo.list_tenant_override_definitions(tenant_id)}
        out: list[PromptListItem] = []
        for d in platform_defs:
            ov = overrides.get(d.prompt_key)
            eff = ov or d
            av = self._active_version(eff.id)
            out.append(
                PromptListItem(
                    prompt_key=d.prompt_key,
                    task_type=d.task_type,
                    title=ov.title if ov else d.title,
                    source="tenant_override" if ov else "platform",
                    definition_id=eff.id,
                    active_version_id=av.id if av else None,
                    active_version_number=av.version_number if av else None,
                )
            )
        for pk, ov in overrides.items():
            if not any(p.prompt_key == pk for p in platform_defs):
                av = self._active_version(ov.id)
                out.append(
                    PromptListItem(
                        prompt_key=ov.prompt_key,
                        task_type=ov.task_type,
                        title=ov.title,
                        source="tenant_override",
                        definition_id=ov.id,
                        active_version_id=av.id if av else None,
                        active_version_number=av.version_number if av else None,
                    )
                )
        out.sort(key=lambda x: x.prompt_key)
        return out

    def get_prompt_detail(self, tenant_id: UUID, definition_id: UUID) -> PromptDetailResponse:
        d = self.repo.get_definition(definition_id)
        if not d:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        if d.scope == PROMPT_SCOPE_TENANT:
            if d.tenant_id != tenant_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        elif d.scope != PROMPT_SCOPE_PLATFORM or d.tenant_id is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        versions = [_version_row(v) for v in self.repo.list_versions(d.id)]
        av = self._active_version(d.id)
        return PromptDetailResponse(
            definition_id=d.id,
            prompt_key=d.prompt_key,
            task_type=d.task_type,
            title=d.title,
            description=d.description,
            scope=d.scope,
            tenant_id=d.tenant_id,
            active_version=_version_row(av) if av else None,
            versions=versions,
        )

    def create_tenant_override(
        self, tenant_id: UUID, actor_id: UUID, prompt_key: str, body: PromptVersionCreateBody, title: str, task_type: str
    ) -> PromptDetailResponse:
        if self.repo.get_tenant_override_definition(tenant_id, prompt_key):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant override already exists")
        if not self.repo.get_platform_definition_by_key(prompt_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown prompt_key (no platform default to override)",
            )
        d = PromptDefinition(
            id=uuid.uuid4(),
            scope=PROMPT_SCOPE_TENANT,
            tenant_id=tenant_id,
            prompt_key=prompt_key,
            title=title,
            description="Tenant override",
            task_type=task_type,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
        )
        self.repo.add_definition(d)
        v = PromptVersion(
            id=uuid.uuid4(),
            prompt_definition_id=d.id,
            version_number=1,
            prompt_text=body.prompt_text,
            change_note=body.change_note,
            created_by_user_id=actor_id,
            is_active=True,
            version_metadata=body.version_metadata,
        )
        self.repo.add_version(v)
        self.repo.add_activation_event(
            PromptActivationEvent(
                id=uuid.uuid4(),
                prompt_definition_id=d.id,
                prompt_version_id=v.id,
                tenant_id=tenant_id,
                actor_user_id=actor_id,
                event_kind="tenant_override_created",
                note=None,
            )
        )
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            event_type="ai.prompt.tenant_override_created",
            details={"prompt_key": prompt_key, "definition_id": str(d.id)},
        )
        self.db.commit()
        return self.get_prompt_detail(tenant_id, d.id)

    def add_version(
        self, tenant_id: UUID, actor_id: UUID, definition_id: UUID, body: PromptVersionCreateBody
    ) -> PromptDetailResponse:
        d = self.repo.get_definition(definition_id)
        if not d or d.scope != PROMPT_SCOPE_TENANT or d.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        n = self.repo.max_version_number(d.id) + 1
        v = PromptVersion(
            id=uuid.uuid4(),
            prompt_definition_id=d.id,
            version_number=n,
            prompt_text=body.prompt_text,
            change_note=body.change_note,
            created_by_user_id=actor_id,
            is_active=False,
            version_metadata=body.version_metadata,
        )
        self.repo.add_version(v)
        d.updated_by_user_id = actor_id
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            event_type="ai.prompt.version_created",
            details={"definition_id": str(d.id), "version_number": n},
        )
        self.db.commit()
        return self.get_prompt_detail(tenant_id, d.id)

    def activate_version(self, tenant_id: UUID, actor_id: UUID, definition_id: UUID, version_id: UUID) -> PromptDetailResponse:
        d = self.repo.get_definition(definition_id)
        if not d:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        if d.scope == PROMPT_SCOPE_TENANT and d.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        if d.scope == PROMPT_SCOPE_PLATFORM:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform prompts cannot be activated via tenant API")
        v = self.repo.get_version(version_id)
        if not v or v.prompt_definition_id != d.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        self.repo.deactivate_all_versions(d.id)
        v.is_active = True
        d.updated_by_user_id = actor_id
        self.repo.add_activation_event(
            PromptActivationEvent(
                id=uuid.uuid4(),
                prompt_definition_id=d.id,
                prompt_version_id=v.id,
                tenant_id=tenant_id,
                actor_user_id=actor_id,
                event_kind="version_activated",
                note=None,
            )
        )
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            event_type="ai.prompt.version_activated",
            details={"definition_id": str(d.id), "version_id": str(v.id), "version_number": v.version_number},
        )
        self.db.commit()
        return self.get_prompt_detail(tenant_id, d.id)

    def revert_to_platform_default(self, tenant_id: UUID, actor_id: UUID, prompt_key: str) -> None:
        ov = self.repo.get_tenant_override_definition(tenant_id, prompt_key)
        if not ov:
            return
        self.repo.delete_definition_cascade(ov)
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            event_type="ai.prompt.reverted_to_platform_default",
            details={"prompt_key": prompt_key},
        )
        self.db.commit()

    def list_versions_for_tenant(self, tenant_id: UUID, definition_id: UUID) -> list[PromptVersionRow]:
        self.get_prompt_detail(tenant_id, definition_id)  # validates access
        return [_version_row(v) for v in self.repo.list_versions(definition_id)]

    def compare_versions(self, tenant_id: UUID, definition_id: UUID, left_id: UUID, right_id: UUID) -> PromptCompareResponse:
        d = self.repo.get_definition(definition_id)
        if not d:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        if d.scope == PROMPT_SCOPE_TENANT and d.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        lv = self.repo.get_version(left_id)
        rv = self.repo.get_version(right_id)
        if not lv or not rv or lv.prompt_definition_id != d.id or rv.prompt_definition_id != d.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        return PromptCompareResponse(
            left=_version_row(lv),
            right=_version_row(rv),
            left_preview=lv.prompt_text[:400],
            right_preview=rv.prompt_text[:400],
        )

    # --- platform ---
    def platform_create_definition(self, actor_id: UUID, body: PlatformPromptDefinitionCreate) -> PromptDetailResponse:
        if self.repo.get_platform_definition_by_key(body.prompt_key):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="prompt_key already exists")
        d = PromptDefinition(
            id=uuid.uuid4(),
            scope=PROMPT_SCOPE_PLATFORM,
            tenant_id=None,
            prompt_key=body.prompt_key,
            title=body.title,
            description=body.description,
            task_type=body.task_type,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
        )
        self.repo.add_definition(d)
        iv = body.initial_version
        v = PromptVersion(
            id=uuid.uuid4(),
            prompt_definition_id=d.id,
            version_number=1,
            prompt_text=iv.prompt_text,
            change_note=iv.change_note,
            created_by_user_id=actor_id,
            is_active=True,
            version_metadata=iv.version_metadata,
        )
        self.repo.add_version(v)
        self.repo.add_activation_event(
            PromptActivationEvent(
                id=uuid.uuid4(),
                prompt_definition_id=d.id,
                prompt_version_id=v.id,
                tenant_id=None,
                actor_user_id=actor_id,
                event_kind="platform_definition_created",
                note=None,
            )
        )
        self.audit.log(
            tenant_id=None,
            actor_user_id=actor_id,
            event_type="ai.prompt.platform_definition_created",
            details={"prompt_key": body.prompt_key, "definition_id": str(d.id)},
        )
        self.db.commit()
        return self.get_prompt_detail_for_platform(d.id)

    def platform_list_prompts(self) -> list[PromptDetailResponse]:
        out = []
        for d in self.repo.list_platform_definitions():
            out.append(self.get_prompt_detail_for_platform(d.id))
        return out

    def get_prompt_detail_for_platform(self, definition_id: UUID) -> PromptDetailResponse:
        d = self.repo.get_definition(definition_id)
        if not d or d.scope != PROMPT_SCOPE_PLATFORM:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        versions = [_version_row(v) for v in self.repo.list_versions(d.id)]
        av = self._active_version(d.id)
        return PromptDetailResponse(
            definition_id=d.id,
            prompt_key=d.prompt_key,
            task_type=d.task_type,
            title=d.title,
            description=d.description,
            scope=d.scope,
            tenant_id=d.tenant_id,
            active_version=_version_row(av) if av else None,
            versions=versions,
        )

    def platform_add_version(self, actor_id: UUID, definition_id: UUID, body: PromptVersionCreateBody) -> PromptDetailResponse:
        d = self.repo.get_definition(definition_id)
        if not d or d.scope != PROMPT_SCOPE_PLATFORM:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        n = self.repo.max_version_number(d.id) + 1
        v = PromptVersion(
            id=uuid.uuid4(),
            prompt_definition_id=d.id,
            version_number=n,
            prompt_text=body.prompt_text,
            change_note=body.change_note,
            created_by_user_id=actor_id,
            is_active=False,
            version_metadata=body.version_metadata,
        )
        self.repo.add_version(v)
        self.audit.log(
            tenant_id=None,
            actor_user_id=actor_id,
            event_type="ai.prompt.platform_version_created",
            details={"definition_id": str(d.id), "version_number": n},
        )
        self.db.commit()
        return self.get_prompt_detail_for_platform(d.id)

    def platform_activate(self, actor_id: UUID, definition_id: UUID, version_id: UUID) -> PromptDetailResponse:
        d = self.repo.get_definition(definition_id)
        if not d or d.scope != PROMPT_SCOPE_PLATFORM:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        v = self.repo.get_version(version_id)
        if not v or v.prompt_definition_id != d.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        self.repo.deactivate_all_versions(d.id)
        v.is_active = True
        self.repo.add_activation_event(
            PromptActivationEvent(
                id=uuid.uuid4(),
                prompt_definition_id=d.id,
                prompt_version_id=v.id,
                tenant_id=None,
                actor_user_id=actor_id,
                event_kind="platform_version_activated",
                note=None,
            )
        )
        self.audit.log(
            tenant_id=None,
            actor_user_id=actor_id,
            event_type="ai.prompt.platform_version_activated",
            details={"definition_id": str(d.id), "version_id": str(v.id)},
        )
        self.db.commit()
        return self.get_prompt_detail_for_platform(d.id)
