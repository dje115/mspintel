from datetime import timedelta
import uuid

from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.entities import Role, Tenant, TenantMembership, User


def create_user_with_membership(db: Session, email: str, role_code: str, tenant: Tenant):
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=email.split("@")[0],
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=False,
    )
    role = db.query(Role).filter(Role.code == role_code).one()
    membership = TenantMembership(
        id=uuid.uuid4(), tenant_id=tenant.id, user_id=user.id, role_id=role.id, status="active"
    )
    db.add_all([user, membership])
    db.commit()
    return user


def auth_headers(user: User, tenant_id: str | None = None, *, session_id: uuid.UUID | None = None):
    token = create_access_token(str(user.id), timedelta(minutes=60), session_id=session_id)
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id
    return headers
