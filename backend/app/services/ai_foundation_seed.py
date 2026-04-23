"""Idempotent seed for AI provider catalog and platform default prompts."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.domain.ai_constants import DEFAULT_PLATFORM_PROMPT_KEYS, PROMPT_SCOPE_PLATFORM
from app.models.entities import (
    AIProvider,
    AIProviderCatalog,
    PromptActivationEvent,
    PromptDefinition,
    PromptVersion,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


CATALOG_ROWS: list[tuple[str, str, str, str, str, int]] = [
    ("openai_hosted", "openai", "hosted", "OpenAI (API)", "Hosted OpenAI API", 10),
    ("azure_openai_hosted", "azure_openai", "hosted", "Azure OpenAI", "Microsoft Azure-hosted OpenAI", 20),
    ("anthropic_hosted", "anthropic", "hosted", "Anthropic", "Hosted Anthropic API", 30),
    ("google_hosted", "google", "hosted", "Google AI / Gemini", "Hosted Google generative AI", 40),
    ("microsoft_copilot_microsoft", "microsoft_copilot", "microsoft", "Microsoft Copilot / M365", "Microsoft-hosted Copilot-aligned path", 50),
    ("openrouter_hosted", "openrouter", "hosted", "OpenRouter", "OpenRouter multi-model gateway", 60),
    ("ollama_local", "ollama", "local", "Ollama", "Local Ollama runtime", 100),
    ("vllm_self", "vllm", "self_hosted", "vLLM", "Self-hosted vLLM server", 110),
    ("lm_studio_local", "lm_studio", "local", "LM Studio", "LM Studio compatible local endpoint", 120),
    ("openai_compatible_self", "openai_compatible", "self_hosted", "OpenAI-compatible API", "Generic OpenAI-compatible base URL", 130),
    ("custom_self", "custom", "self_hosted", "Custom provider", "Future custom adapter", 200),
]


def ensure_ai_provider_catalog(db: "Session") -> None:
    existing = db.scalar(select(func.count()).select_from(AIProviderCatalog))
    if existing and int(existing) > 0:
        return
    for code, fam, mode, title, desc, sort in CATALOG_ROWS:
        db.add(
            AIProviderCatalog(
                id=uuid.uuid4(),
                code=code,
                provider_family=fam,
                deployment_mode=mode,
                display_name=title,
                description=desc,
                sort_order=sort,
            )
        )
    db.commit()


def ensure_platform_default_prompts(db: "Session") -> None:
    for prompt_key, task_type, title in DEFAULT_PLATFORM_PROMPT_KEYS:
        exists = db.scalars(
            select(PromptDefinition).where(
                PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
                PromptDefinition.tenant_id.is_(None),
                PromptDefinition.prompt_key == prompt_key,
            )
        ).first()
        if exists:
            continue
        d = PromptDefinition(
            id=uuid.uuid4(),
            scope=PROMPT_SCOPE_PLATFORM,
            tenant_id=None,
            prompt_key=prompt_key,
            title=title,
            description=f"Platform default for {prompt_key}",
            task_type=task_type,
            created_by_user_id=None,
            updated_by_user_id=None,
        )
        db.add(d)
        db.flush()
        v = PromptVersion(
            id=uuid.uuid4(),
            prompt_definition_id=d.id,
            version_number=1,
            prompt_text=f"You are an MSP intelligence assistant. Task context: {task_type}. Follow tenant policies and produce concise, actionable output.",
            change_note="Initial platform version",
            created_by_user_id=None,
            is_active=True,
            version_metadata=None,
        )
        db.add(v)
    db.commit()


def ensure_legacy_prompt_aliases(db: "Session") -> None:
    """If older platform keys exist without the canonical route-aligned key, clone active text once."""
    alias_map: list[tuple[str, str, str, str]] = [
        ("customer360.summary", "account_summary.system", "account_summary", "Account / Customer 360 summary"),
    ]
    for old_key, new_key, task_type, title in alias_map:
        has_new = db.scalars(
            select(PromptDefinition).where(
                PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
                PromptDefinition.tenant_id.is_(None),
                PromptDefinition.prompt_key == new_key,
            )
        ).first()
        if has_new:
            continue
        old_def = db.scalars(
            select(PromptDefinition).where(
                PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
                PromptDefinition.tenant_id.is_(None),
                PromptDefinition.prompt_key == old_key,
            )
        ).first()
        if not old_def:
            continue
        av = db.scalars(
            select(PromptVersion)
            .where(PromptVersion.prompt_definition_id == old_def.id, PromptVersion.is_active.is_(True))
            .limit(1)
        ).first()
        body = av.prompt_text if av else f"You are an MSP intelligence assistant. Task context: {task_type}."
        nd = PromptDefinition(
            id=uuid.uuid4(),
            scope=PROMPT_SCOPE_PLATFORM,
            tenant_id=None,
            prompt_key=new_key,
            title=title,
            description=f"Cloned from legacy key {old_key}",
            task_type=task_type,
            created_by_user_id=None,
            updated_by_user_id=None,
        )
        db.add(nd)
        db.flush()
        nv = PromptVersion(
            id=uuid.uuid4(),
            prompt_definition_id=nd.id,
            version_number=1,
            prompt_text=body,
            change_note=f"Alias of {old_key}",
            created_by_user_id=None,
            is_active=True,
            version_metadata=None,
        )
        db.add(nv)
        db.flush()
        db.add(
            PromptActivationEvent(
                id=uuid.uuid4(),
                prompt_definition_id=nd.id,
                prompt_version_id=nv.id,
                tenant_id=None,
                actor_user_id=None,
                event_kind="platform_alias_created",
                note=None,
            )
        )
    db.commit()


def ensure_demo_tenant_ai_provider(db: "Session", tenant_id: uuid.UUID) -> None:
    """Attach catalog metadata to the first tenant OpenAI row if present."""
    row = db.scalars(select(AIProvider).where(AIProvider.tenant_id == tenant_id).limit(1)).first()
    if row and not row.provider_family:
        row.catalog_code = "openai_hosted"
        row.provider_family = "openai"
        row.deployment_mode = "hosted"
        row.display_label = "OpenAI (demo)"
        row.is_enabled = True
        db.commit()
