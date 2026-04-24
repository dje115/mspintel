from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer, SourceEntityMapping, SourceSystemConnection, Tenant
from app.services.connectors.providers.autotask import AutotaskConnectorAdapter
from tests.helpers import auth_headers, create_user_with_membership


def _make_tenant(db: Session, *, slug: str, name: str) -> Tenant:
    t = Tenant(id=uuid.uuid4(), slug=slug, name=name, is_active=True)
    db.add(t)
    db.commit()
    return t


def test_create_connection_redacts_secrets_and_lists_per_tenant(client, db_session: Session):
    tenant_a = _make_tenant(db_session, slug="alpha", name="Alpha MSP")
    tenant_b = _make_tenant(db_session, slug="beta", name="Beta MSP")
    admin_a = create_user_with_membership(db_session, "admin-a@example.com", "tenant_admin", tenant_a)
    _admin_b = create_user_with_membership(db_session, "admin-b@example.com", "tenant_admin", tenant_b)

    payload = {
        "system_type": "autotask",
        "display_name": "Alpha Autotask",
        "base_url": "https://example.autotask.net/ATServicesRest",
        "auth_mode": "api_key",
        "is_enabled": True,
        "sync_cadence_minutes": 30,
        "config": {"username": "api-user", "integration_code": "code-1", "secret": "super-secret"},
    }
    r = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin_a, str(tenant_a.id)),
        json=payload,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["system_type"] == "autotask"
    assert body["safe_config"]["secret"] == "[redacted]"
    assert "super-secret" not in str(body)

    list_a = client.get("/api/v1/integrations/connections", headers=auth_headers(admin_a, str(tenant_a.id)))
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["display_name"] == "Alpha Autotask"

    admin_b = db_session.scalar(
        select(SourceSystemConnection).where(SourceSystemConnection.tenant_id == tenant_b.id)
    )
    assert admin_b is None


def test_itquoter_stub_test_connection_returns_safe_failure(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="gamma", name="Gamma MSP")
    admin = create_user_with_membership(db_session, "admin-gamma@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "itquoter",
            "display_name": "ITQuoter staged",
            "sync_cadence_minutes": 120,
            "config": {},
        },
    )
    assert create.status_code == 201, create.text
    cid = create.json()["id"]
    t = client.post(f"/api/v1/integrations/connections/{cid}/test", headers=auth_headers(admin, str(tenant.id)))
    assert t.status_code == 200, t.text
    body = t.json()
    assert body["test_status"] == "failed"
    assert "not implemented" in (body["test_message"] or "").lower()


def test_autotask_sync_writes_customers_mappings_and_run(monkeypatch, client, db_session: Session):
    tenant = _make_tenant(db_session, slug="delta", name="Delta MSP")
    admin = create_user_with_membership(db_session, "admin-delta@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "autotask",
            "display_name": "Delta Autotask",
            "base_url": "https://example.autotask.net/ATServicesRest",
            "sync_cadence_minutes": 30,
            "config": {"username": "api", "integration_code": "code", "secret": "sec"},
        },
    )
    assert create.status_code == 201, create.text
    cid = create.json()["id"]

    def fake_fetch(self, base_url: str, headers: dict[str, str], path: str, since_cursor: str | None):
        if "Companies" in path:
            return [{"id": 101, "companyName": "Northwind Managed", "ownerResourceName": "A. Owner"}]
        if "Contacts" in path:
            return [{"id": 201, "companyID": 101, "firstName": "Mina", "lastName": "Lopez", "emailAddress": "mina@northwind.test"}]
        if "Tickets" in path:
            return [{"id": 301, "companyID": 101, "status": "Open", "title": "Backup job failing"}]
        if "Opportunities" in path:
            return [{"id": 401, "companyID": 101, "status": "Open", "title": "M365 uplift", "amount": 1250}]
        if "Quotes" in path:
            return [{"id": 501, "companyID": 101, "status": "lost", "name": "Endpoint refresh", "totalAmount": 9800}]
        return []

    monkeypatch.setattr(AutotaskConnectorAdapter, "_fetch_entities", fake_fetch)
    monkeypatch.setattr(AutotaskConnectorAdapter, "_base_url", lambda self, connection, config: "https://unused")

    run = client.post(f"/api/v1/integrations/connections/{cid}/sync", headers=auth_headers(admin, str(tenant.id)))
    assert run.status_code == 202, run.text
    run_body = run.json()
    assert run_body["status"] == "succeeded"
    assert run_body["records_processed"] == 5

    customers = db_session.scalars(select(Customer).where(Customer.tenant_id == tenant.id)).all()
    assert len(customers) == 1
    assert customers[0].name == "Northwind Managed"

    mappings = db_session.scalars(select(SourceEntityMapping).where(SourceEntityMapping.tenant_id == tenant.id)).all()
    assert len(mappings) >= 5

    runs = client.get(f"/api/v1/integrations/connections/{cid}/runs", headers=auth_headers(admin, str(tenant.id)))
    assert runs.status_code == 200
    assert runs.json()[0]["status"] == "succeeded"
    assert runs.json()[0]["started_at"] is not None

    # Ensure this test stays deterministic with cursor updates
    conn = db_session.get(SourceSystemConnection, uuid.UUID(cid))
    assert conn is not None
    assert conn.last_sync_at is not None
    assert conn.last_successful_sync_at is not None
    assert datetime.fromisoformat(conn.connection_metadata["last_cursor"].replace("Z", "+00:00")).tzinfo == UTC
