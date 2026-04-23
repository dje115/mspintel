import uuid

from app.models.entities import Customer, Tenant
from tests.helpers import auth_headers, create_user_with_membership


def test_executive_dashboard_tenant_scoped(client, db_session):
    ta = Tenant(id=uuid.uuid4(), slug="da", name="DA", is_active=True)
    tb = Tenant(id=uuid.uuid4(), slug="db", name="DB", is_active=True)
    db_session.add_all([ta, tb])
    db_session.commit()

    user = create_user_with_membership(db_session, "dash@example.com", "tenant_admin", ta)

    db_session.add_all(
        [
            Customer(id=uuid.uuid4(), tenant_id=ta.id, name="CA", status="active", owner_name="o"),
            Customer(id=uuid.uuid4(), tenant_id=tb.id, name="CB", status="active", owner_name="o"),
        ]
    )
    db_session.commit()

    ok = client.get("/api/v1/dashboards/executive", headers=auth_headers(user, str(ta.id)))
    assert ok.status_code == 200

    denied = client.get("/api/v1/dashboards/executive", headers=auth_headers(user, str(tb.id)))
    assert denied.status_code == 403
