import uuid

from sqlalchemy import select

from app.models.entities import Tenant, TenantMembership, User
from app.repositories.memberships import MembershipRepository
from tests.helpers import create_user_with_membership


def test_count_active_tenant_admins(db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="r1", name="R1", is_active=True)
    db_session.add(tenant)
    db_session.commit()

    create_user_with_membership(db_session, "adm1@example.com", "tenant_admin", tenant)
    create_user_with_membership(db_session, "adm2@example.com", "tenant_admin", tenant)
    create_user_with_membership(db_session, "sales@example.com", "sales_user", tenant)

    repo = MembershipRepository(db_session)
    assert repo.count_active_tenant_admins(tenant.id) == 2

    sales = db_session.scalars(select(User).where(User.email == "sales@example.com")).one()
    m = db_session.scalars(
        select(TenantMembership).where(TenantMembership.user_id == sales.id, TenantMembership.tenant_id == tenant.id)
    ).one()
    m.status = "suspended"
    db_session.commit()

    assert repo.count_active_tenant_admins(tenant.id) == 2
