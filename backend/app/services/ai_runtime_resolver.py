"""Resolve provider, model, and active prompt for a tenant AI task (foundation for runners)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.ai_constants import AI_TASK_TYPES
from app.models.entities import AIProvider, AITaskRun, PromptVersion
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


def apply_prompt_and_provider_lineage(run: AITaskRun, resolved: ResolvedAITask) -> None:
    """Copy provider/model and prompt ids from a ``ResolvedAITask`` onto a run row (single source)."""
    run.provider_family = resolved.provider_family
    run.deployment_mode = resolved.deployment_mode
    run.model_used = resolved.model
    run.ai_provider_id = resolved.ai_provider_id
    run.prompt_definition_id = resolved.prompt_definition_id
    run.prompt_version_id = resolved.prompt_version_id


class AIRuntimeResolver:
    def __init__(self, db: Session):
        self.db = db
        self.tenant_repo = TenantAiConfigRepository(db)
        self.prompt_repo = PromptRegistryRepository(db)

    def _provider_for_tenant(self, provider_id: UUID | None, tenant_id: UUID) -> AIProvider | None:
        if not provider_id:
            return None
        prov = self.db.get(AIProvider, provider_id)
        if prov and prov.tenant_id != tenant_id:
            return None
        return prov

    def _active_version_for_definition(self, definition_id: UUID) -> PromptVersion | None:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_definition_id == definition_id, PromptVersion.is_active.is_(True))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def resolve(self, tenant_id: UUID, task_type: str, *, include_prompt_text: bool = True) -> ResolvedAITask:
        if task_type in AI_TASK_TYPES:
            self.tenant_repo.ensure_task_route_stub(tenant_id, task_type)
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
        prov = self._provider_for_tenant(route.ai_provider_id, tenant_id)
        if not prov and settings and settings.default_ai_provider_id:
            prov = self._provider_for_tenant(settings.default_ai_provider_id, tenant_id)

        model = route.model or (settings.default_model if settings else None)

        fb_prov = self._provider_for_tenant(route.fallback_ai_provider_id, tenant_id)
        if not fb_prov and settings and settings.fallback_ai_provider_id:
            fb_prov = self._provider_for_tenant(settings.fallback_ai_provider_id, tenant_id)
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
        row = self.db.get(AITaskRun, run_id)
        if not row:
            return
        apply_prompt_and_provider_lineage(row, resolved)
        row.status = status
        row.duration_ms = duration_ms
        row.run_metadata = run_metadata
        self.db.flush()
