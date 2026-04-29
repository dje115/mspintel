from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AuditEvent, ConnectorMappingReview, Customer, SourceEntityMapping, SourceSystemConnection, Tenant
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


def test_connector_catalog_exposes_manifest_metadata(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="catalog", name="Catalog MSP")
    admin = create_user_with_membership(db_session, "admin-catalog@example.com", "tenant_admin", tenant)
    res = client.get("/api/v1/integrations/catalog", headers=auth_headers(admin, str(tenant.id)))
    assert res.status_code == 200, res.text
    rows = res.json()
    autotask = next(r for r in rows if r["system_type"] == "autotask")
    assert autotask["maturity"] in ("beta", "stable", "experimental")
    assert "api_key" in autotask["supported_auth_modes"]
    assert isinstance(autotask["config_fields"], list)
    itquoter = next(r for r in rows if r["system_type"] == "itquoter")
    assert itquoter["implemented"] is False
    assert itquoter["maturity"] in ("stub", "planned")


def test_create_connection_rejects_unsupported_auth_mode(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="bad-auth", name="Bad Auth MSP")
    admin = create_user_with_membership(db_session, "admin-bad-auth@example.com", "tenant_admin", tenant)
    r = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "autotask",
            "display_name": "Bad auth",
            "auth_mode": "oauth2",
            "sync_cadence_minutes": 30,
            "config": {"username": "u", "integration_code": "i", "secret": "s", "base_url": "https://example"},
        },
    )
    assert r.status_code == 400
    assert "Unsupported auth_mode" in r.text


def test_create_connection_rejects_missing_required_manifest_config(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="missing-cfg", name="Missing Config MSP")
    admin = create_user_with_membership(db_session, "admin-missing-cfg@example.com", "tenant_admin", tenant)
    r = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "autotask",
            "display_name": "Missing bits",
            "auth_mode": "api_key",
            "sync_cadence_minutes": 30,
            "config": {"username": "u"},
        },
    )
    assert r.status_code == 400
    assert "Missing connector config keys" in r.text


def test_autotask_connector_lab_connection_test_success(monkeypatch, client, db_session: Session):
    tenant = _make_tenant(db_session, slug="autotest", name="Autotask Test MSP")
    admin = create_user_with_membership(db_session, "admin-autotest@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "autotask",
            "display_name": "Autotask Connector Lab",
            "base_url": "http://connector-lab:8099/autotask",
            "sync_cadence_minutes": 30,
            "config": {"api_key": "connector-lab-api-key"},
        },
    )
    assert create.status_code == 201, create.text
    cid = create.json()["id"]

    class _FakeResponse:
        def __init__(self, status_code: int, payload: dict | None = None):
            self.status_code = status_code
            self._payload = payload or {}
            self.content = b"{}"

        def json(self):
            return self._payload

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url: str, headers=None, params=None):
            if url.endswith("/health"):
                return _FakeResponse(200, {"status": "ok"})
            if url.endswith("/accounts"):
                return _FakeResponse(200, {"items": [{"id": "A-1"}]})
            return _FakeResponse(404, {})

    monkeypatch.setattr(httpx, "Client", _FakeClient)
    tested = client.post(f"/api/v1/integrations/connections/{cid}/test", headers=auth_headers(admin, str(tenant.id)))
    assert tested.status_code == 200, tested.text
    body = tested.json()
    assert body["test_status"] == "succeeded"
    assert "accounts endpoint checks passed" in (body["test_message"] or "").lower()


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


def test_autotask_sync_skips_unmapped_accounts_when_customer_baseline_exists(monkeypatch, client, db_session: Session):
    tenant = _make_tenant(db_session, slug="delta-skip", name="Delta Skip MSP")
    admin = create_user_with_membership(db_session, "admin-delta-skip@example.com", "tenant_admin", tenant)
    baseline = Customer(tenant_id=tenant.id, name="Known Baseline Co", status="active")
    db_session.add(baseline)
    db_session.commit()
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "autotask",
            "display_name": "Delta Autotask",
            "base_url": "http://connector-lab:8099/autotask",
            "sync_cadence_minutes": 30,
            "config": {"api_key": "connector-lab-api-key"},
        },
    )
    assert create.status_code == 201, create.text
    cid = create.json()["id"]

    def fake_fetch(self, base_url: str, headers: dict[str, str], path: str, since_cursor: str | None):
        if "accounts" in path:
            return [{"id": "AT-404", "companyName": "Unmatched External Co", "ownerResourceName": "Owner X"}]
        return []

    monkeypatch.setattr(AutotaskConnectorAdapter, "_fetch_entities", fake_fetch)
    run = client.post(f"/api/v1/integrations/connections/{cid}/sync", headers=auth_headers(admin, str(tenant.id)))
    assert run.status_code == 202, run.text
    body = run.json()
    assert body["status"] == "succeeded"
    assert body["records_processed"] == 0
    warnings = (body.get("stats_json") or {}).get("warnings") or []
    assert any("requires mapping review" in w.lower() for w in warnings)
    customers = db_session.scalars(select(Customer).where(Customer.tenant_id == tenant.id)).all()
    assert len(customers) == 1
    mapping_rows = db_session.scalars(
        select(ConnectorMappingReview).where(ConnectorMappingReview.tenant_id == tenant.id)
    ).all()
    assert len(mapping_rows) == 1
    assert mapping_rows[0].status in {"pending", "unlinked"}


def test_lifecycle_and_import_scope_updates_are_audited(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="life", name="Lifecycle MSP")
    admin = create_user_with_membership(db_session, "admin-life@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "microsoft_365",
            "display_name": "M365 staged",
            "auth_mode": "sandbox",
            "sync_cadence_minutes": 60,
            "config": {"demo_mode": True},
        },
    )
    assert create.status_code == 201, create.text
    cid = create.json()["id"]
    life = client.patch(
        f"/api/v1/integrations/connections/{cid}/lifecycle",
        headers=auth_headers(admin, str(tenant.id)),
        json={"lifecycle_state": "paused", "is_paused": True, "sync_behavior": "manual_sync_only"},
    )
    assert life.status_code == 200, life.text
    assert life.json()["lifecycle_state"] == "paused"
    scope = client.patch(
        f"/api/v1/integrations/connections/{cid}/import-scope",
        headers=auth_headers(admin, str(tenant.id)),
        json={"import_scope_mode": "sample_limit", "filters": {"sample_limit": 10}},
    )
    assert scope.status_code == 200, scope.text
    assert scope.json()["import_scope_mode"] == "sample_limit"
    events = db_session.scalars(select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)).all()
    assert any(e.event_type == "connector_lifecycle_updated" for e in events)
    assert any(e.event_type == "connector_import_scope_updated" for e in events)


def test_mapping_review_action_remap_and_unlink(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="mapq", name="Mapping Queue MSP")
    admin = create_user_with_membership(db_session, "admin-mapq@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "autotask",
            "display_name": "Auto",
            "base_url": "https://example.autotask.net/ATServicesRest",
            "sync_cadence_minutes": 30,
            "config": {"username": "api", "integration_code": "code", "secret": "sec"},
        },
    )
    assert create.status_code == 201, create.text
    cid = uuid.UUID(create.json()["id"])
    customer = Customer(tenant_id=tenant.id, name="Acme Ltd", status="active")
    db_session.add(customer)
    db_session.flush()
    review = ConnectorMappingReview(
        tenant_id=tenant.id,
        source_connection_id=cid,
        entity_type="customer",
        source_external_id="ext-123",
        source_display_name="Acme Limited",
        suggested_customer_id=customer.id,
        suggested_confidence="medium",
        status="pending",
    )
    db_session.add(review)
    db_session.commit()

    rows = client.get("/api/v1/integrations/mappings", headers=auth_headers(admin, str(tenant.id)))
    assert rows.status_code == 200
    assert len(rows.json()) >= 1
    action = client.post(
        f"/api/v1/integrations/mappings/{review.id}/action",
        headers=auth_headers(admin, str(tenant.id)),
        json={"action": "remap", "customer_id": str(customer.id)},
    )
    assert action.status_code == 200, action.text
    assert action.json()["status"] == "remapped"
    unlink = client.post(
        f"/api/v1/integrations/mappings/{review.id}/action",
        headers=auth_headers(admin, str(tenant.id)),
        json={"action": "unlink"},
    )
    assert unlink.status_code == 200, unlink.text
    assert unlink.json()["status"] == "unlinked"
    mapping = db_session.scalars(
        select(SourceEntityMapping).where(
            SourceEntityMapping.tenant_id == tenant.id, SourceEntityMapping.source_id == "ext-123"
        )
    ).first()
    assert mapping is None


def test_mapping_review_action_rejects_cross_tenant_customer(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="mapx", name="Mapping Isolated MSP")
    other_tenant = _make_tenant(db_session, slug="other-x", name="Other Tenant")
    admin = create_user_with_membership(db_session, "admin-mapx@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "autotask",
            "display_name": "Auto",
            "base_url": "https://example.autotask.net/ATServicesRest",
            "sync_cadence_minutes": 30,
            "config": {"username": "api", "integration_code": "code", "secret": "sec"},
        },
    )
    assert create.status_code == 201, create.text
    cid = uuid.UUID(create.json()["id"])
    tenant_customer = Customer(tenant_id=tenant.id, name="Tenant Co", status="active")
    other_customer = Customer(tenant_id=other_tenant.id, name="Other Co", status="active")
    db_session.add(tenant_customer)
    db_session.add(other_customer)
    db_session.flush()
    review = ConnectorMappingReview(
        tenant_id=tenant.id,
        source_connection_id=cid,
        entity_type="customer",
        source_external_id="ext-safe-1",
        source_display_name="Tenant Company",
        suggested_customer_id=tenant_customer.id,
        suggested_confidence="medium",
        status="pending",
    )
    db_session.add(review)
    db_session.commit()

    bad = client.post(
        f"/api/v1/integrations/mappings/{review.id}/action",
        headers=auth_headers(admin, str(tenant.id)),
        json={"action": "remap", "customer_id": str(other_customer.id)},
    )
    assert bad.status_code == 404
    assert "Target customer not found" in bad.text


def test_mapping_review_list_supports_filters(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="mapfilter", name="Mapping Filter MSP")
    admin = create_user_with_membership(db_session, "admin-mapfilter@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "autotask",
            "display_name": "Auto",
            "base_url": "https://example.autotask.net/ATServicesRest",
            "sync_cadence_minutes": 30,
            "config": {"username": "api", "integration_code": "code", "secret": "sec"},
        },
    )
    assert create.status_code == 201, create.text
    cid = uuid.UUID(create.json()["id"])
    customer = Customer(tenant_id=tenant.id, name="Filter Co", status="active")
    db_session.add(customer)
    db_session.flush()
    db_session.add_all(
        [
            ConnectorMappingReview(
                tenant_id=tenant.id,
                source_connection_id=cid,
                entity_type="customer",
                source_external_id="fil-1",
                source_display_name="Filter Company Ltd",
                suggested_customer_id=customer.id,
                suggested_confidence="medium",
                status="pending",
            ),
            ConnectorMappingReview(
                tenant_id=tenant.id,
                source_connection_id=cid,
                entity_type="customer",
                source_external_id="fil-2",
                source_display_name="Another Company",
                suggested_confidence="low",
                status="rejected",
            ),
        ]
    )
    db_session.commit()

    pending = client.get(
        "/api/v1/integrations/mappings?status_filter=pending&search=Filter",
        headers=auth_headers(admin, str(tenant.id)),
    )
    assert pending.status_code == 200, pending.text
    body = pending.json()
    assert len(body) == 1
    assert body[0]["source_external_id"] == "fil-1"
    assert isinstance(body[0]["eligible_for_customer_create"], bool)
    assert isinstance(body[0]["create_customer_blockers"], list)


def test_mapping_import_creates_customers_and_is_idempotent(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="mapimport", name="Mapping Import MSP")
    admin = create_user_with_membership(db_session, "admin-mapimport@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "microsoft_365",
            "display_name": "M365",
            "auth_mode": "sandbox",
            "sync_cadence_minutes": 60,
            "config": {"demo_mode": True},
        },
    )
    assert create.status_code == 201, create.text
    cid = uuid.UUID(create.json()["id"])
    review_a = ConnectorMappingReview(
        tenant_id=tenant.id,
        source_connection_id=cid,
        entity_type="customer",
        source_external_id="m365-customer:acme",
        source_display_name="Acme Dental Ltd",
        source_domain="acme-dental.co.uk",
        suggested_confidence="low",
        status="unlinked",
    )
    review_b = ConnectorMappingReview(
        tenant_id=tenant.id,
        source_connection_id=cid,
        entity_type="customer",
        source_external_id="m365-customer:bright",
        source_display_name="Bright Legal Services",
        source_domain="bright-legal.co.uk",
        suggested_confidence="low",
        status="pending",
    )
    db_session.add_all([review_a, review_b])
    db_session.commit()

    imported = client.post(
        "/api/v1/integrations/mappings/create-customers",
        headers=auth_headers(admin, str(tenant.id)),
        json={"connection_id": str(cid)},
    )
    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["eligible_rows"] == 2
    assert body["created_customers"] == 2
    assert body["accepted_rows"] == 2
    assert body["skipped_rows"] == 0

    reviews_after = db_session.scalars(
        select(ConnectorMappingReview).where(ConnectorMappingReview.tenant_id == tenant.id)
    ).all()
    assert all(r.status == "accepted" for r in reviews_after)
    assert all(r.mapped_customer_id is not None for r in reviews_after)
    customers = db_session.scalars(select(Customer).where(Customer.tenant_id == tenant.id)).all()
    assert len(customers) == 2

    rerun = client.post(
        "/api/v1/integrations/mappings/create-customers",
        headers=auth_headers(admin, str(tenant.id)),
        json={"connection_id": str(cid)},
    )
    assert rerun.status_code == 200, rerun.text
    rerun_body = rerun.json()
    assert rerun_body["created_customers"] == 0
    assert rerun_body["accepted_rows"] == 0
    customers_after_rerun = db_session.scalars(select(Customer).where(Customer.tenant_id == tenant.id)).all()
    assert len(customers_after_rerun) == 2

    audit_rows = db_session.scalars(select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)).all()
    assert any(a.event_type == "connector_mapping_customers_imported" for a in audit_rows)


def test_integration_coverage_endpoint_shapes_counts(client, db_session: Session):
    tenant = _make_tenant(db_session, slug="cov", name="Coverage MSP")
    admin = create_user_with_membership(db_session, "admin-cov@example.com", "tenant_admin", tenant)
    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "microsoft_365",
            "display_name": "M365",
            "auth_mode": "sandbox",
            "sync_cadence_minutes": 60,
            "config": {"demo_mode": True},
        },
    )
    assert create.status_code == 201, create.text
    cid = uuid.UUID(create.json()["id"])
    customer = Customer(tenant_id=tenant.id, name="Coverage Co", status="active")
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        SourceEntityMapping(
            tenant_id=tenant.id,
            source_connection_id=cid,
            entity_type="customer",
            source_id="cov-1",
            canonical_entity_id=customer.id,
        )
    )
    db_session.add(
        ConnectorMappingReview(
            tenant_id=tenant.id,
            source_connection_id=cid,
            entity_type="customer",
            source_external_id="cov-pending",
            suggested_confidence="medium",
            status="pending",
        )
    )
    db_session.commit()
    res = client.get("/api/v1/integrations/coverage", headers=auth_headers(admin, str(tenant.id)))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["connected_systems"] == 1
    assert body["unresolved_mappings"] == 1
    assert body["items"][0]["linked_customers"] == 1
