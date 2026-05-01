"""End-to-end AI task execution: resolve → render → adapter → ai_task_runs."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.ai_constants import (
    AI_RUN_FAILED,
    AI_RUN_QUEUED,
    AI_RUN_RUNNING,
    AI_RUN_SKIPPED,
    AI_RUN_SUCCEEDED,
    AI_RUN_UNAVAILABLE,
    AI_RUN_UNSUPPORTED,
)
from app.models.entities import AIProvider, AITaskRun
from app.repositories.ai_task_runs import AITaskRunRepository
from app.schemas.ai_execution import AIExecutionOutcome, AIProductBlockState
from app.services.ai_prompt_render import render_prompt_template
from app.services.ai_providers.base import ProviderNotConfiguredError, ProviderTransportError, ProviderUnsupportedError
from app.services.ai_providers.registry import execute_chat_completion, is_family_runnable
from app.services.ai_runtime_resolver import AIRuntimeResolver, ResolvedAITask
from app.core.ai_settings_crypto import decrypt_settings_payload
from app.services.ai_runtime_resolver import apply_prompt_and_provider_lineage
from app.services.ai_task_variable_policy import prepare_llm_variables


def _effective_model(provider_family: str | None, model: str | None) -> str:
    m = (model or "").strip()
    if m:
        return m
    if provider_family in ("ollama", "vllm", "lm_studio", "openai_compatible"):
        return "llama3.2"
    return "gpt-4o-mini"


def _decrypt_provider_settings(row: AIProvider) -> dict[str, Any]:
    if not row.encrypted_settings:
        return {}
    try:
        out = decrypt_settings_payload(row.encrypted_settings)
        return out if isinstance(out, dict) else {}
    except ValueError:
        return {}


def _finalize_run(
    db: Session,
    run: AITaskRun,
    *,
    resolved: ResolvedAITask,
    status: str,
    duration_ms: int | None,
    error_summary: str | None,
    output_summary: str | None,
    fallback_used: bool,
    run_metadata: dict[str, Any] | None,
) -> None:
    now = datetime.now(UTC)
    run.status = status
    run.duration_ms = duration_ms
    run.error_summary = error_summary
    run.output_summary = output_summary
    run.fallback_used = fallback_used
    run.completed_at = now
    apply_prompt_and_provider_lineage(run, resolved)
    run.run_metadata = run_metadata
    db.flush()


def _outcome_from_run(run: AITaskRun, resolved: ResolvedAITask, *, message: str | None = None) -> AIExecutionOutcome:
    meta = run.run_metadata or {}
    text = meta.get("assistant_text") if isinstance(meta, dict) else None
    return AIExecutionOutcome(
        run_id=run.id,
        status=run.status,
        task_type=run.task_type,
        text=text if isinstance(text, str) else run.output_summary,
        message=message or run.error_summary,
        provider_family=run.provider_family,
        deployment_mode=run.deployment_mode,
        model_used=run.model_used,
        prompt_definition_id=run.prompt_definition_id,
        prompt_version_id=run.prompt_version_id,
        fallback_used=run.fallback_used,
        duration_ms=run.duration_ms,
        completed_at=run.completed_at,
    )


def _invoke_model(
    *,
    resolved: ResolvedAITask,
    provider_row: AIProvider,
    system_prompt: str,
    user_message: str,
    use_fallback_fields: bool,
) -> tuple[str, dict[str, Any]]:
    fam = (
        resolved.fallback_provider_family
        if use_fallback_fields
        else resolved.provider_family
    )
    mode = (
        resolved.fallback_deployment_mode
        if use_fallback_fields
        else resolved.deployment_mode
    )
    model = _effective_model(
        fam,
        resolved.fallback_model if use_fallback_fields else resolved.model,
    )
    settings = _decrypt_provider_settings(provider_row)
    result = execute_chat_completion(
        provider_family=fam or "openai",
        settings=settings,
        base_url=provider_row.base_url,
        model=model,
        system_prompt=system_prompt,
        user_content=user_message,
    )
    meta = {"provider_family": fam, "deployment_mode": mode, "model": model, "raw_finish": result.raw.get("choices", [{}])[0].get("finish_reason")}
    return result.text, meta


class AIExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AITaskRunRepository(db)

    def read_block_state(
        self,
        tenant_id: UUID,
        task_type: str,
        *,
        customer_id: UUID | None = None,
        recommendation_id: UUID | None = None,
    ) -> AIProductBlockState:
        row = self.repo.latest_for(
            tenant_id, task_type, customer_id=customer_id, recommendation_id=recommendation_id
        )
        if not row:
            return AIProductBlockState(status="not_generated", message="No AI run yet for this context.")
        if row.status == AI_RUN_SUCCEEDED:
            meta = row.run_metadata or {}
            text = meta.get("assistant_text") if isinstance(meta, dict) else None
            return AIProductBlockState(
                status="succeeded",
                text=text if isinstance(text, str) else row.output_summary,
                run_id=row.id,
                last_completed_at=row.completed_at,
                provider_family=row.provider_family,
                model_used=row.model_used,
                prompt_version_id=row.prompt_version_id,
            )
        if row.status in (AI_RUN_FAILED, AI_RUN_UNSUPPORTED, AI_RUN_UNAVAILABLE, AI_RUN_SKIPPED):
            return AIProductBlockState(
                status=row.status,
                message=row.error_summary or row.status,
                run_id=row.id,
                last_completed_at=row.completed_at,
            )
        return AIProductBlockState(status=row.status, message="Run in progress or queued.", run_id=row.id)

    def execute(
        self,
        *,
        tenant_id: UUID,
        task_type: str,
        variables: dict[str, Any],
        actor_user_id: UUID | None,
        customer_id: UUID | None = None,
        recommendation_id: UUID | None = None,
    ) -> AIExecutionOutcome:
        resolver = AIRuntimeResolver(self.db)
        resolved = resolver.resolve(tenant_id, task_type, include_prompt_text=True)

        run = AITaskRun(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            task_type=task_type,
            status=AI_RUN_QUEUED,
            actor_user_id=actor_user_id,
            customer_id=customer_id,
            recommendation_id=recommendation_id,
        )
        self.db.add(run)
        self.db.flush()

        t0 = time.perf_counter()

        if not resolved.enabled:
            _finalize_run(
                self.db,
                run,
                resolved=resolved,
                status=AI_RUN_SKIPPED,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                error_summary=None,
                output_summary=None,
                fallback_used=False,
                run_metadata={"reason": "task_disabled"},
            )
            self.db.commit()
            return _outcome_from_run(run, resolved, message="This AI task is disabled for your tenant.")

        if not resolved.prompt_text or not resolved.prompt_definition_id:
            _finalize_run(
                self.db,
                run,
                resolved=resolved,
                status=AI_RUN_UNAVAILABLE,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                error_summary="No active prompt version for this task.",
                output_summary=None,
                fallback_used=False,
                run_metadata={"prompt_key": resolved.prompt_key},
            )
            self.db.commit()
            return _outcome_from_run(
                run,
                resolved,
                message=(
                    "No active prompt is configured for this task. "
                    "Sync platform defaults: `docker compose exec backend python -m app.scripts.sync_platform_prompt_defaults` "
                    "or activate a prompt version in tenant/platform prompts."
                ),
            )

        llm_variables = prepare_llm_variables(task_type, variables)
        system_prompt = render_prompt_template(resolved.prompt_text, llm_variables)
        user_message = json.dumps(llm_variables, ensure_ascii=False, indent=2)

        primary_row = self.db.get(AIProvider, resolved.ai_provider_id) if resolved.ai_provider_id else None
        if not primary_row or primary_row.tenant_id != tenant_id:
            _finalize_run(
                self.db,
                run,
                resolved=resolved,
                status=AI_RUN_UNAVAILABLE,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                error_summary="No tenant AI provider resolved for this task.",
                output_summary=None,
                fallback_used=False,
                run_metadata=None,
            )
            self.db.commit()
            return _outcome_from_run(
                run, resolved, message="Configure a default AI provider or a task-specific provider in AI settings."
            )

        if not is_family_runnable(resolved.provider_family):
            _finalize_run(
                self.db,
                run,
                resolved=resolved,
                status=AI_RUN_UNSUPPORTED,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                error_summary=f"Provider family {resolved.provider_family!r} is not runnable in this release.",
                output_summary=None,
                fallback_used=False,
                run_metadata={"provider_family": resolved.provider_family},
            )
            self.db.commit()
            return _outcome_from_run(run, resolved, message="This provider type is not executable yet in mspintel.")

        run.started_at = datetime.now(UTC)
        run.status = AI_RUN_RUNNING
        self.db.flush()

        fb_used = False
        last_err: str | None = None
        assistant_text: str | None = None
        extra_meta: dict[str, Any] = {}

        def _attempt(use_fallback: bool) -> bool:
            nonlocal assistant_text, extra_meta, last_err
            if use_fallback:
                prow = self.db.get(AIProvider, resolved.fallback_ai_provider_id) if resolved.fallback_ai_provider_id else None
                if not prow or prow.tenant_id != tenant_id:
                    return False
                if not is_family_runnable(resolved.fallback_provider_family):
                    return False
                try:
                    assistant_text, extra_meta = _invoke_model(
                        resolved=resolved,
                        provider_row=prow,
                        system_prompt=system_prompt,
                        user_message=user_message,
                        use_fallback_fields=True,
                    )
                    return True
                except (ProviderUnsupportedError, ProviderNotConfiguredError, ProviderTransportError) as exc:
                    last_err = str(exc)
                    return False
            try:
                assistant_text, extra_meta = _invoke_model(
                    resolved=resolved,
                    provider_row=primary_row,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    use_fallback_fields=False,
                )
                return True
            except (ProviderUnsupportedError, ProviderNotConfiguredError, ProviderTransportError) as exc:
                last_err = str(exc)
                return False

        ok = _attempt(False)
        if not ok and resolved.fallback_ai_provider_id:
            ok = _attempt(True)
            fb_used = ok

        duration_ms = int((time.perf_counter() - t0) * 1000)
        if ok and assistant_text:
            preview = assistant_text[:2000]
            meta = {"assistant_text": assistant_text, **extra_meta}
            eff = resolved
            if fb_used and resolved.fallback_ai_provider_id:
                eff = ResolvedAITask(
                    tenant_id=resolved.tenant_id,
                    task_type=resolved.task_type,
                    enabled=resolved.enabled,
                    provider_family=resolved.fallback_provider_family,
                    deployment_mode=resolved.fallback_deployment_mode,
                    model=_effective_model(resolved.fallback_provider_family, resolved.fallback_model),
                    ai_provider_id=resolved.fallback_ai_provider_id,
                    prompt_key=resolved.prompt_key,
                    prompt_definition_id=resolved.prompt_definition_id,
                    prompt_version_id=resolved.prompt_version_id,
                    prompt_text=resolved.prompt_text,
                    fallback_ai_provider_id=resolved.fallback_ai_provider_id,
                    fallback_provider_family=resolved.fallback_provider_family,
                    fallback_deployment_mode=resolved.fallback_deployment_mode,
                    fallback_model=resolved.fallback_model,
                )
            _finalize_run(
                self.db,
                run,
                resolved=eff,
                status=AI_RUN_SUCCEEDED,
                duration_ms=duration_ms,
                error_summary=None,
                output_summary=preview,
                fallback_used=fb_used,
                run_metadata=meta,
            )
            self.db.commit()
            return _outcome_from_run(run, eff)

        err = last_err or "Model call failed"
        _finalize_run(
            self.db,
            run,
            resolved=resolved,
            status=AI_RUN_FAILED,
            duration_ms=duration_ms,
            error_summary=err[:2000],
            output_summary=None,
            fallback_used=fb_used,
            run_metadata={"last_error": err[:500]},
        )
        self.db.commit()
        return _outcome_from_run(run, resolved, message="The AI provider returned an error. Check AI settings and credentials.")
