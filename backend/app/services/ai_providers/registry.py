"""Dispatch chat completion by provider family."""

from __future__ import annotations

from typing import Any

from app.domain.ai_constants import OPENAI_COMPATIBLE_FAMILIES
from app.services.ai_providers.base import (
    ChatCompletionResult,
    ProviderNotConfiguredError,
    ProviderUnsupportedError,
)
from app.services.ai_providers.openai_compatible import chat_completion_sync


def is_family_runnable(family: str | None) -> bool:
    return bool(family and family in OPENAI_COMPATIBLE_FAMILIES)


def execute_chat_completion(
    *,
    provider_family: str,
    settings: dict[str, Any],
    base_url: str | None,
    model: str,
    system_prompt: str,
    user_content: str,
) -> ChatCompletionResult:
    if provider_family in OPENAI_COMPATIBLE_FAMILIES:
        api_key = (settings or {}).get("api_key") or (settings or {}).get("openai_api_key")
        bu = base_url or (settings or {}).get("base_url")
        return chat_completion_sync(
            base_url=bu if isinstance(bu, str) else None,
            api_key=api_key if isinstance(api_key, str) else None,
            model=model,
            system_prompt=system_prompt,
            user_content=user_content,
        )
    if provider_family == "azure_openai":
        raise ProviderUnsupportedError(
            "Azure OpenAI requires endpoint + api_version wiring; use openai_compatible family with a full base URL "
            "or wait for a dedicated adapter."
        )
    if provider_family in ("anthropic", "google", "microsoft_copilot", "custom"):
        raise ProviderUnsupportedError(f"Provider family {provider_family!r} is adapter-ready but not runnable in this release.")
    raise ProviderUnsupportedError(f"Unknown provider family {provider_family!r}")
