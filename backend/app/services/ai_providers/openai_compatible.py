"""OpenAI-compatible ``/v1/chat/completions`` (OpenAI, OpenRouter, Ollama, vLLM, LM Studio, generic)."""

from __future__ import annotations

from typing import Any

import httpx

from app.services.ai_providers.base import ChatCompletionResult, ProviderNotConfiguredError, ProviderTransportError


def _normalize_base_url(base_url: str | None) -> str:
    if not base_url or not str(base_url).strip():
        return "https://api.openai.com/v1"
    u = str(base_url).rstrip("/")
    if u.endswith("/v1"):
        return u
    if "/v1" in u:
        return u.split("/v1")[0] + "/v1"
    return u + "/v1"


def chat_completion_sync(
    *,
    base_url: str | None,
    api_key: str | None,
    model: str,
    system_prompt: str,
    user_content: str,
    timeout_s: float = 90.0,
) -> ChatCompletionResult:
    root = _normalize_base_url(base_url)
    url = f"{root}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
    }
    if not model:
        raise ProviderNotConfiguredError("model is required")

    try:
        with httpx.Client(timeout=timeout_s) as client:
            r = client.post(url, headers=headers, json=payload)
    except httpx.RequestError as exc:
        raise ProviderTransportError(str(exc)) from exc

    if r.status_code >= 400:
        raise ProviderTransportError(r.text[:500] or f"HTTP {r.status_code}", status_code=r.status_code)

    data = r.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderTransportError(f"Unexpected response shape: {data!r:.400}") from exc
    if not isinstance(text, str):
        raise ProviderTransportError("Model returned non-string content")
    return ChatCompletionResult(text=text.strip(), raw=data)
