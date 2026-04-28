import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    ConnectorMappingReview,
    Contact,
    Customer,
    IntegrationSyncRun,
    M365CustomerPosture,
    Opportunity,
    Quote,
    Recommendation,
    SourceSystemConnection,
    Tenant,
    Ticket,
)
from app.services.connectors.providers.microsoft_365 import Microsoft365ConnectorAdapter
from app.services.seed import seed_all


def _login(client, email: str, password: str) -> tuple[str, str]:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    tenant_id = me.json()["memberships"][0]["tenant_id"]
    return token, tenant_id


def _tenant_id(db: Session) -> uuid.UUID:
    tenant = db.scalars(select(Tenant).where(Tenant.slug == "demo-msp")).first()
    assert tenant is not None
    return tenant.id


def test_seed_all_is_structural_only_and_resets_business_rows(db_session: Session):
    seed_all(db_session)
    seed_all(db_session)  # reseed should clear prior demo business data and stay structural-only
    tenant_id = _tenant_id(db_session)

    assert db_session.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).first() is None
    assert db_session.scalars(select(Contact).where(Contact.tenant_id == tenant_id)).first() is None
    assert db_session.scalars(select(Ticket).where(Ticket.tenant_id == tenant_id)).first() is None
    assert db_session.scalars(select(Opportunity).where(Opportunity.tenant_id == tenant_id)).first() is None
    assert db_session.scalars(select(Quote).where(Quote.tenant_id == tenant_id)).first() is None
    assert db_session.scalars(select(Recommendation).where(Recommendation.tenant_id == tenant_id)).first() is None
    assert db_session.scalars(select(M365CustomerPosture).where(M365CustomerPosture.tenant_id == tenant_id)).first() is None
    assert db_session.scalars(select(IntegrationSyncRun).where(IntegrationSyncRun.tenant_id == tenant_id)).first() is None

    conns = list(db_session.scalars(select(SourceSystemConnection).where(SourceSystemConnection.tenant_id == tenant_id)).all())
    assert len(conns) >= 5
    assert any(c.system_type == "microsoft_365" for c in conns)
    assert any(c.base_url and "connector-lab" in c.base_url for c in conns)


def test_m365_posture_appears_only_after_connector_sync(client, db_session: Session, monkeypatch):
    seed_all(db_session)
    token, tenant_id = _login(client, "tenant-admin@demo-msp.example.com", "ChangeMe123!")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id}
    tid = uuid.UUID(tenant_id)

    assert db_session.scalars(select(M365CustomerPosture).where(M365CustomerPosture.tenant_id == tid)).first() is None

    def _fake_fetch(self, *, base_url: str, path: str, config: dict, page_size: int = 200):
        if path == "tenants":
            return [{"id": "M-T900", "tenant_name": "seed-sync.onmicrosoft.com", "customer_hint": "Seed Sync Customer Ltd"}]
        if path == "licence-summary":
            return [{"tenant_id": "M-T900", "licensed_users": 21, "active_users_30d": 19, "inactive_users_30d": 2}]
        if path == "mailbox-counts":
            return [{"tenant_id": "M-T900", "mailboxes": 19, "shared_mailboxes": 3}]
        if path == "hygiene-findings":
            return [{"tenant_id": "M-T900", "finding": "inactive_users_still_licensed"}]
        return []

    monkeypatch.setattr(Microsoft365ConnectorAdapter, "_fetch_resource", _fake_fetch)

    conn_res = client.get("/api/v1/integrations/connections", headers=headers)
    assert conn_res.status_code == 200, conn_res.text
    m365 = next((c for c in conn_res.json() if c["system_type"] == "microsoft_365"), None)
    assert m365 is not None

    sync = client.post(f"/api/v1/integrations/connections/{m365['id']}/sync", headers=headers)
    assert sync.status_code == 202, sync.text
    assert sync.json()["status"] == "succeeded"
    # Structural-only seed means unmatched source rows should queue for mapping review,
    # not auto-create canonical customers.
    assert sync.json()["records_processed"] == 0
    assert db_session.scalars(select(M365CustomerPosture).where(M365CustomerPosture.tenant_id == tid)).first() is None
    reviews = db_session.scalars(select(ConnectorMappingReview).where(ConnectorMappingReview.tenant_id == tid)).all()
    assert len(reviews) >= 1
    assert any(r.status in {"pending", "unlinked"} for r in reviews)


def test_workspace_apis_are_safe_after_structural_only_seed(client, db_session: Session):
    seed_all(db_session)
    token, tenant_id = _login(client, "tenant-admin@demo-msp.example.com", "ChangeMe123!")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id}

    endpoints = [
        "/api/v1/workspace/recommendations",
        "/api/v1/workspace/commercial",
        "/api/v1/workspace/service-risk",
        "/api/v1/workspace/billing-integrity",
        "/api/v1/workspace/m365-health",
        "/api/v1/customers",
    ]
    for url in endpoints:
        res = client.get(url, headers=headers)
        assert res.status_code == 200, f"{url} -> {res.status_code}: {res.text}"
