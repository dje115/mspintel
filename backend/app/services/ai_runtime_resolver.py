"""Resolve provider, model, and active prompt for a tenant AI task (foundation for runners)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AIProvider, PromptVersion, TenantAiSettings
from app.repositories.prompt_registry import PromptRegistryRepository
from app.repositories.tenant_ai_config import TenantAiConfigRepository


@dataclass
class ResolvedAITask:
    tenant_id: UUID
    task_type: str
    enabled: bool
    provider_family: str | None
    deployment_mode: str | None
    model: str | None
    ai_provider_id: UUID | None
    prompt_key: str
    prompt_definition_id: UUID | None
    prompt_version_id: UUID | None
    prompt_text: str | None
    fallback_ai_provider_id: UUID | None = None
    fallback_provider_family: str | None = None
    fallback_deployment_mode: str | None = None
    fallback_model: str | None = None


class AIRuntimeResolver:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_repo = TenantAiConfigRepository(db)
        self.prompt_repo = PromptRegistryRepository(db)

    def _active_version_for_definition(self, definition_id: UUID) -> PromptVersion | None:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_definition_id == definition_id, PromptVersion.is_active.is_(True))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def resolve(self, tenant_id: UUID, task_type: str, *, include_prompt_text: bool = True) -> ResolvedAITask:
        route = self.tenant_repo.get_route_by_task(tenant_id, task_type)
        if not route:
            return ResolvedAITask(
                tenant_id=tenant_id,
                task_type=task_type,
                enabled=False,
                provider_family=None,
                deployment_mode=None,
                model=None,
                ai_provider_id=None,
                prompt_key=f"{task_type}.system",
                prompt_definition_id=None,
                prompt_version_id=None,
                prompt_text=None,
            )
        if not route.enabled:
            return ResolvedAITask(
                tenant_id=tenant_id,
                task_type=task_type,
                enabled=False,
                provider_family=None,
                deployment_mode=None,
                model=route.model,
                ai_provider_id=route.ai_provider_id,
                prompt_key=route.prompt_key,
                prompt_definition_id=None,
                prompt_version_id=None,
                prompt_text=None,
            )

        settings = self.tenant_repo.get_settings(tenant_id)
        prov: AIProvider | None = None
        if route.ai_provider_id:
            prov = self.db.get(AIProvider, route.ai_provider_id)
            if prov and prov.tenant_id != tenant_id:
                prov = None
        if not prov and settings and settings.default_ai_provider_id:
            prov = self.db.get(AIProvider, settings.default_ai_provider_id)
            if prov and prov.tenant_id != tenant_id:
                prov = None

        model = route.model or (settings.default_model if settings else None)

        fb_prov: AIProvider | None = None
        if route.fallback_ai_provider_id:
            fb_prov = self.db.get(AIProvider, route.fallback_ai_provider_id)
            if fb_prov and fb_prov.tenant_id != tenant_id:
                fb_prov = None
        if not fb_prov and settings and settings.fallback_ai_provider_id:
            fb_prov = self.db.get(AIProvider, settings.fallback_ai_provider_id)
            if fb_prov and fb_prov.tenant_id != tenant_id:
                fb_prov = None
        fb_model = route.fallback_model or (settings.fallback_model if settings else None)

        tenant_def = self.prompt_repo.get_tenant_override_definition(tenant_id, route.prompt_key)
        platform_def = self.prompt_repo.get_platform_definition_by_key(route.prompt_key)
        eff_def = tenant_def or platform_def
        pv: PromptVersion | None = None
        if eff_def:
            pv = self._active_version_for_definition(eff_def.id)

        return ResolvedAITask(
            tenant_id=tenant_id,
            task_type=task_type,
            enabled=True,
            provider_family=prov.provider_family if prov else None,
            deployment_mode=prov.deployment_mode if prov else None,
            model=model,
            ai_provider_id=prov.id if prov else None,
            prompt_key=route.prompt_key,
            prompt_definition_id=eff_def.id if eff_def else None,
            prompt_version_id=pv.id if pv else None,
            prompt_text=pv.prompt_text if pv and include_prompt_text else None,
            fallback_ai_provider_id=fb_prov.id if fb_prov else None,
            fallback_provider_family=fb_prov.provider_family if fb_prov else None,
            fallback_deployment_mode=fb_prov.deployment_mode if fb_prov else None,
            fallback_model=fb_model,
        )

    def record_task_run_lineage(
        self,
        *,
        run_id: UUID,
        tenant_id: UUID,
        resolved: ResolvedAITask,
        status: str,
        duration_ms: int | None = None,
        run_metadata: dict | None = None,
    ) -> None:
        from app.models.entities import AITaskRun

        row = self.db.get(AITaskRun, run_id)
        if not row:
            return
        row.provider_family = resolved.provider_family
        row.deployment_mode = resolved.deployment_mode
        row.model_used = resolved.model
        row.ai_provider_id = resolved.ai_provider_id
        row.prompt_definition_id = resolved.prompt_definition_id
        row.prompt_version_id = resolved.prompt_version_id
        row.status = status
        row.duration_ms = duration_ms
        row.run_metadata = run_metadata
        self.db.flush()
