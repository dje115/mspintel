from dataclasses import dataclass

from fastapi import Header


@dataclass(frozen=True)
class AccessContext:
    """Request-level access context.

    This is intentionally simple for scaffold stage. It creates a stable shape where
    authentication, tenant membership, and platform-role checks can be enforced later.
    """

    user_id: str | None
    tenant_slug: str | None
    platform_role: str


def get_access_context(
    x_user_id: str | None = Header(default=None),
    x_tenant_slug: str | None = Header(default=None),
    x_platform_role: str | None = Header(default="user"),
) -> AccessContext:
    return AccessContext(
        user_id=x_user_id,
        tenant_slug=x_tenant_slug,
        platform_role=x_platform_role or "user",
    )
