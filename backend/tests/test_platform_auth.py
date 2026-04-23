import uuid

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.entities import Tenant, User
from tests.helpers import create_user_with_membership, platform_password_login


def test_tenant_login_rejects_platform_admin(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="p1", name="P1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = User(
        id=uuid.uuid4(),
        email="plat@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(admin)
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": "plat@example.com", "password": "ChangeMe123!"})
    assert res.status_code == 403
    assert "platform" in res.json()["detail"].lower()


def test_platform_login_rejects_non_admin(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="p2", name="P2", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    u = create_user_with_membership(db_session, "member@example.com", "sales_user", tenant)

    res = client.post("/api/v1/auth/platform/login", json={"email": u.email, "password": "ChangeMe123!"})
    assert res.status_code == 401


def test_platform_login_ok(client, db_session: Session):
    admin = User(
        id=uuid.uuid4(),
        email="plat2@example.com",
        full_name="Plat2",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(admin)
    db_session.commit()

    body = platform_password_login(client, "plat2@example.com", "ChangeMe123!")
    assert body["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["auth_mode"] == "platform"
    assert me.json()["is_platform_admin"] is True


def test_platform_token_cannot_hit_tenant_customers(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="p3", name="P3", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = User(
        id=uuid.uuid4(),
        email="plat3@example.com",
        full_name="Plat3",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    pair = platform_password_login(client, "plat3@example.com", "ChangeMe123!")
    res = client.get(
        "/api/v1/customers?page=1&page_size=10",
        headers={"Authorization": f"Bearer {pair['access_token']}", "X-Tenant-Id": str(tenant.id)},
    )
    assert res.status_code == 403


def test_platform_overview_ok(client, db_session: Session):
    admin = User(
        id=uuid.uuid4(),
        email="plat4@example.com",
        full_name="Plat4",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    pair = platform_password_login(client, "plat4@example.com", "ChangeMe123!")
    res = client.get("/api/v1/platform/overview", headers={"Authorization": f"Bearer {pair['access_token']}"})
    assert res.status_code == 200
    body = res.json()
    assert "tenant_count" in body
    assert "app_version" in body


def test_tenant_token_cannot_hit_platform_overview(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="p4", name="P4", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    u = create_user_with_membership(db_session, "sales2@example.com", "sales_user", tenant)
    pair = client.post("/api/v1/auth/login", json={"email": u.email, "password": "ChangeMe123!"}).json()
    res = client.get(
        "/api/v1/platform/overview",
        headers={"Authorization": f"Bearer {pair['access_token']}", "X-Tenant-Id": str(tenant.id)},
    )
    assert res.status_code == 403
