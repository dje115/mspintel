import uuid

from sqlalchemy import func, select

from app.models.entities import AuditEvent, Role, Tenant, TenantMembership, User
from tests.helpers import auth_headers, create_user_with_membership


def _tenant(db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="m1", name="M1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    return tenant


def test_patch_member_role_success(client, db_session):
    tenant = _tenant(db_session)
    admin = create_user_with_membership(db_session, "m-admin@example.com", "tenant_admin", tenant)
    member = create_user_with_membership(db_session, "m-member@example.com", "sales_user", tenant)

    members = client.get("/api/v1/tenants/current/members", headers=auth_headers(admin, str(tenant.id))).json()
    mid = next(m["membership_id"] for m in members if m["email"] == "m-member@example.com")

    res = client.patch(
        f"/api/v1/tenants/current/members/{mid}",
        json={"role_code": "director"},
        headers=auth_headers(admin, str(tenant.id)),
    )
    assert res.status_code == 200
    assert res.json()["role_code"] == "director"

    row = db_session.scalars(select(TenantMembership).where(TenantMembership.id == uuid.UUID(mid))).one()
    role = db_session.scalars(select(Role).where(Role.id == row.role_id)).one()
    assert role.code == "director"


def test_patch_member_denied_for_non_admin(client, db_session):
    tenant = _tenant(db_session)
    admin = create_user_with_membership(db_session, "m-ad2@example.com", "tenant_admin", tenant)
    sales = create_user_with_membership(db_session, "m-sales@example.com", "sales_user", tenant)

    members = client.get("/api/v1/tenants/current/members", headers=auth_headers(admin, str(tenant.id))).json()
    mid = next(m["membership_id"] for m in members if m["email"] == "m-sales@example.com")

    res = client.patch(
        f"/api/v1/tenants/current/members/{mid}",
        json={"role_code": "director"},
        headers=auth_headers(sales, str(tenant.id)),
    )
    assert res.status_code == 403


def test_patch_member_cross_tenant_returns_404(client, db_session):
    ta = Tenant(id=uuid.uuid4(), slug="a", name="A", is_active=True)
    tb = Tenant(id=uuid.uuid4(), slug="b", name="B", is_active=True)
    db_session.add_all([ta, tb])
    db_session.commit()

    admin_a = create_user_with_membership(db_session, "a-only@example.com", "tenant_admin", ta)
    create_user_with_membership(db_session, "b-user@example.com", "tenant_admin", tb)

    b_membership = db_session.scalars(
        select(TenantMembership).join(User).where(User.email == "b-user@example.com")
    ).one()

    res = client.patch(
        f"/api/v1/tenants/current/members/{b_membership.id}",
        json={"role_code": "sales_user"},
        headers=auth_headers(admin_a, str(ta.id)),
    )
    assert res.status_code == 404


def test_patch_membership_no_op_skips_audit(client, db_session):
    tenant = _tenant(db_session)
    admin = create_user_with_membership(db_session, "noop-ad@example.com", "tenant_admin", tenant)
    member = create_user_with_membership(db_session, "noop-m@example.com", "sales_user", tenant)

    before = db_session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_type == "membership.updated"))

    members = client.get("/api/v1/tenants/current/members", headers=auth_headers(admin, str(tenant.id))).json()
    mid = next(m["membership_id"] for m in members if m["email"] == "noop-m@example.com")

    res = client.patch(
        f"/api/v1/tenants/current/members/{mid}",
        json={"role_code": "sales_user"},
        headers=auth_headers(admin, str(tenant.id)),
    )
    assert res.status_code == 200
    after = db_session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_type == "membership.updated"))
    assert after == before


def test_patch_blank_role_rejected(client, db_session):
    tenant = _tenant(db_session)
    admin = create_user_with_membership(db_session, "blank-ad@example.com", "tenant_admin", tenant)
    member = create_user_with_membership(db_session, "blank-m@example.com", "sales_user", tenant)

    members = client.get("/api/v1/tenants/current/members", headers=auth_headers(admin, str(tenant.id))).json()
    mid = next(m["membership_id"] for m in members if m["email"] == "blank-m@example.com")

    res = client.patch(
        f"/api/v1/tenants/current/members/{mid}",
        json={"role_code": "   "},
        headers=auth_headers(admin, str(tenant.id)),
    )
    assert res.status_code == 400


def test_cannot_demote_last_tenant_admin(client, db_session):
    tenant = _tenant(db_session)
    sole = create_user_with_membership(db_session, "sole@example.com", "tenant_admin", tenant)

    members = client.get("/api/v1/tenants/current/members", headers=auth_headers(sole, str(tenant.id))).json()
    mid = next(m["membership_id"] for m in members if m["email"] == "sole@example.com")

    res = client.patch(
        f"/api/v1/tenants/current/members/{mid}",
        json={"role_code": "sales_user"},
        headers=auth_headers(sole, str(tenant.id)),
    )
    assert res.status_code == 400
    assert "last active tenant admin" in res.json()["detail"].lower()
