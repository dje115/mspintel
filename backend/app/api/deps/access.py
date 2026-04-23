from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.db import get_db
from app.core.security import decode_access_token, decode_access_token_payload
from app.models.entities import Role, Tenant, TenantMembership, User

security = HTTPBearer(auto_error=False)


@dataclass
class AccessContext:
    user: User
    tenant: Tenant
    membership: TenantMembership
    role_code: str
    is_platform_admin: bool
    current_session_id: UUID | None = None


ROLE_PERMISSIONS = {
    "platform_admin": {
        "system:read",
        "tenant:read",
        "membership:read",
        "membership:write",
        "invitation:read",
        "invitation:write",
        "customer:read",
        "dashboard:executive",
        "dashboard:sales",
        "dashboard:service",
    },
    "tenant_admin": {
        "tenant:read",
        "membership:read",
        "membership:write",
        "invitation:read",
        "invitation:write",
        "customer:read",
        "onboarding:write",
        "dashboard:executive",
        "dashboard:sales",
        "dashboard:service",
        "system:read",
    },
    "director": {"customer:read", "dashboard:executive", "membership:read", "invitation:read"},
    "sales_user": {"customer:read", "dashboard:sales"},
    "account_manager": {"customer:read", "dashboard:executive"},
    "service_manager": {"customer:read", "dashboard:service"},
    "marketing_user": {"customer:read", "dashboard:executive"},
}


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        return None
    return db.get(User, UUID(user_id))


def get_access_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_tenant_id: UUID | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AccessContext:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

    payload = decode_access_token_payload(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

    user_id = str(payload["sub"])
    sid_raw = payload.get("sid")
    try:
        current_session_id: UUID | None = UUID(str(sid_raw)) if sid_raw else None
    except ValueError:
        current_session_id = None

    user = db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    membership_query = (
        select(TenantMembership, Tenant, Role)
        .join(Tenant, TenantMembership.tenant_id == Tenant.id)
        .join(Role, TenantMembership.role_id == Role.id)
        .where(TenantMembership.user_id == user.id, TenantMembership.status == "active")
    )
    if x_tenant_id:
        membership_query = membership_query.where(TenantMembership.tenant_id == x_tenant_id)

    row = db.execute(membership_query).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant membership access")

    membership, tenant, role = row
    return AccessContext(
        user=user,
        tenant=tenant,
        membership=membership,
        role_code=role.code,
        is_platform_admin=user.is_platform_admin,
        current_session_id=current_session_id,
    )


def require_permission(permission: str):
    def checker(ctx: AccessContext = Depends(get_access_context)) -> AccessContext:
        if ctx.is_platform_admin:
            return ctx
        allowed = ROLE_PERMISSIONS.get(ctx.role_code, set())
        if permission not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return ctx

    return checker
