import uuid

from sqlalchemy import select

from app.models.entities import AuditEvent, Tenant, TenantInvitation, TenantMembership, User
from tests.helpers import auth_headers, create_user_with_membership


def test_tenant_admin_can_invite_and_list(client, db_session, monkeypatch):
    monkeypatch.setattr("app.services.mail.MailService.send", lambda *args, **kwargs: None)

    tenant = Tenant(id=uuid.uuid4(), slug="demo", name="Demo", is_active=True)
    db_session.add(tenant)
    db_session.commit()

    admin = create_user_with_membership(db_session, "admin@example.com", "tenant_admin", tenant)

    res = client.post(
        "/api/v1/tenants/current/invitations",
        json={"email": "newuser@example.com", "role_to_assign": "sales_user"},
        headers=auth_headers(admin, str(tenant.id)),
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "pending"
    assert payload["accept_url"]
    assert payload["debug_token"] is None

    list_res = client.get(
        "/api/v1/tenants/current/invitations", headers=auth_headers(admin, str(tenant.id))
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_normal_user_cannot_invite(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="demo2", name="Demo2", is_active=True)
    db_session.add(tenant)
    db_session.commit()

    sales = create_user_with_membership(db_session, "sales@example.com", "sales_user", tenant)

    res = client.post(
        "/api/v1/tenants/current/invitations",
        json={"email": "blocked@example.com", "role_to_assign": "sales_user"},
        headers=auth_headers(sales, str(tenant.id)),
    )
    assert res.status_code == 403


def test_accept_invite_new_user_flow(client, db_session, monkeypatch):
    monkeypatch.setattr("app.services.mail.MailService.send", lambda *args, **kwargs: None)

    tenant = Tenant(id=uuid.uuid4(), slug="demo3", name="Demo3", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "admin3@example.com", "tenant_admin", tenant)

    client.post(
        "/api/v1/tenants/current/invitations",
        json={"email": "new-invite@example.com", "role_to_assign": "sales_user"},
        headers=auth_headers(admin, str(tenant.id)),
    )
    invite = db_session.scalars(
        select(TenantInvitation).where(
            TenantInvitation.tenant_id == tenant.id,
            TenantInvitation.email == "new-invite@example.com",
        )
    ).one()

    accept_res = client.post(
        "/api/v1/invitations/accept",
        json={"token": invite.token, "full_name": "Invited User", "password": "ChangeMe123!"},
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"

    invite = db_session.scalars(select(TenantInvitation).where(TenantInvitation.id == invite.id)).one()
    assert invite.status == "accepted"

    user = db_session.scalars(select(User).where(User.email == "new-invite@example.com")).one()
    membership = db_session.scalars(
        select(TenantMembership).where(TenantMembership.tenant_id == tenant.id, TenantMembership.user_id == user.id)
    ).one()
    assert membership.status == "active"

    audit_events = db_session.scalars(
        select(AuditEvent).where(AuditEvent.tenant_id == tenant.id, AuditEvent.event_type == "invitation.accepted")
    ).all()
    assert len(audit_events) == 1


def test_existing_account_requires_login_for_invite_accept(client, db_session, monkeypatch):
    monkeypatch.setattr("app.services.mail.MailService.send", lambda *args, **kwargs: None)

    tenant = Tenant(id=uuid.uuid4(), slug="demo4", name="Demo4", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "admin4@example.com", "tenant_admin", tenant)

    existing_user = User(
        id=uuid.uuid4(),
        email="existing@example.com",
        full_name="Existing",
        password_hash="$invalid",
        is_platform_admin=False,
    )
    db_session.add(existing_user)
    db_session.commit()

    client.post(
        "/api/v1/tenants/current/invitations",
        json={"email": "existing@example.com", "role_to_assign": "sales_user"},
        headers=auth_headers(admin, str(tenant.id)),
    )
    invite = db_session.scalars(
        select(TenantInvitation).where(TenantInvitation.tenant_id == tenant.id, TenantInvitation.email == "existing@example.com")
    ).one()

    res = client.post(
        "/api/v1/invitations/accept",
        json={"token": invite.token, "full_name": "Ignored", "password": "IgnoredPassword123!"},
    )
    assert res.status_code == 409
