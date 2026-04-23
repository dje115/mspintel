import uuid

from app.models.entities import Customer, Tenant
from tests.helpers import auth_headers, create_user_with_membership


def test_customer_list_is_tenant_scoped(client, db_session):
    tenant_a = Tenant(id=uuid.uuid4(), slug="a", name="A", is_active=True)
    tenant_b = Tenant(id=uuid.uuid4(), slug="b", name="B", is_active=True)
    db_session.add_all([tenant_a, tenant_b])
    db_session.commit()

    user = create_user_with_membership(db_session, "sales-scope@example.com", "sales_user", tenant_a)

    db_session.add_all(
        [
            Customer(id=uuid.uuid4(), tenant_id=tenant_a.id, name="A Customer", status="active", owner_name="A"),
            Customer(id=uuid.uuid4(), tenant_id=tenant_b.id, name="B Customer", status="active", owner_name="B"),
        ]
    )
    db_session.commit()

    res = client.get("/api/v1/customers", headers=auth_headers(user, str(tenant_a.id)))
    assert res.status_code == 200
    names = [item["name"] for item in res.json()["items"]]
    assert "A Customer" in names
    assert "B Customer" not in names


def test_cross_tenant_access_denied_without_membership(client, db_session):
    tenant_a = Tenant(id=uuid.uuid4(), slug="a2", name="A2", is_active=True)
    tenant_b = Tenant(id=uuid.uuid4(), slug="b2", name="B2", is_active=True)
    db_session.add_all([tenant_a, tenant_b])
    db_session.commit()

    user = create_user_with_membership(db_session, "sales-cross@example.com", "sales_user", tenant_a)

    res = client.get("/api/v1/customers", headers=auth_headers(user, str(tenant_b.id)))
    assert res.status_code == 403
