import uuid

from app.models.entities import Customer, Recommendation, Tenant
from tests.helpers import auth_headers, create_user_with_membership


def test_workspace_recommendations_tenant_scoped(client, db_session):
    ta = Tenant(id=uuid.uuid4(), slug="wa", name="WA", is_active=True)
    tb = Tenant(id=uuid.uuid4(), slug="wb", name="WB", is_active=True)
    db_session.add_all([ta, tb])
    db_session.commit()

    user = create_user_with_membership(db_session, "ws-rec@example.com", "tenant_admin", ta)
    ca = Customer(id=uuid.uuid4(), tenant_id=ta.id, name="CA", status="active", owner_name="o")
    cb = Customer(id=uuid.uuid4(), tenant_id=tb.id, name="CB", status="active", owner_name="o")
    db_session.add_all([ca, cb])
    db_session.flush()
    db_session.add(
        Recommendation(
            id=uuid.uuid4(),
            tenant_id=ta.id,
            customer_id=ca.id,
            scope="executive",
            status="open",
            summary="Do the thing",
        )
    )
    db_session.add(
        Recommendation(
            id=uuid.uuid4(),
            tenant_id=tb.id,
            customer_id=cb.id,
            scope="executive",
            status="open",
            summary="Other tenant",
        )
    )
    db_session.commit()

    ok = client.get("/api/v1/workspace/recommendations", headers=auth_headers(user, str(ta.id)))
    assert ok.status_code == 200
    body = ok.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["summary"] == "Do the thing"

    denied = client.get("/api/v1/workspace/recommendations", headers=auth_headers(user, str(tb.id)))
    assert denied.status_code == 403


def test_workspace_commercial_and_service_risk_ok(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="wc", name="WC", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "ws-com@example.com", "account_manager", tenant)

    r1 = client.get("/api/v1/workspace/commercial", headers=auth_headers(user, str(tenant.id)))
    assert r1.status_code == 200
    assert "opportunities" in r1.json()
    assert "lost_quotes" in r1.json()

    r2 = client.get("/api/v1/workspace/service-risk", headers=auth_headers(user, str(tenant.id)))
    assert r2.status_code == 200
    b = r2.json()
    assert b["backup"]["placeholder"] is True
    assert "open_tickets" in b["service_delivery"]["metrics"]


def test_patch_recommendation_requires_admin(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="wp", name="WP", is_active=True)
    db_session.add(tenant)
    db_session.flush()
    c = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="C", status="active", owner_name="o")
    db_session.add(c)
    db_session.flush()
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        customer_id=c.id,
        scope="executive",
        status="open",
        summary="x",
    )
    db_session.add(rec)
    db_session.commit()

    director = create_user_with_membership(db_session, "ws-dir@example.com", "director", tenant)
    bad = client.patch(
        f"/api/v1/workspace/recommendations/{rec.id}",
        headers=auth_headers(director, str(tenant.id)),
        json={"status": "accepted"},
    )
    assert bad.status_code == 403

    admin = create_user_with_membership(db_session, "ws-adm@example.com", "tenant_admin", tenant)
    good = client.patch(
        f"/api/v1/workspace/recommendations/{rec.id}",
        headers=auth_headers(admin, str(tenant.id)),
        json={"status": "accepted"},
    )
    assert good.status_code == 200
    assert good.json()["status"] == "accepted"
