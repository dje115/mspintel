from __future__ import annotations

from starlette.requests import Request


def client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua.strip() if ua else None


def device_label_from_user_agent(user_agent_value: str | None, max_len: int = 120) -> str | None:
    if not user_agent_value:
        return None
    s = user_agent_value.strip()
    if not s:
        return None
    return s[:max_len]
