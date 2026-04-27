from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Customer, M365CustomerPosture, SourceEntityMapping, SourceSystemConnection, Tenant
from app.services.connectors.registry import ConnectorRegistry
from tests.helpers import auth_headers, create_user_with_membership


def _tenant(db: Session, slug: str) -> Tenant:
    t = Tenant(id=uuid.uuid4(), slug=slug, name=slug.title(), is_active=True)
    db.add(t)
    db.commit()
    return t


def test_m365_manifest_exposed() -> None:
    m = ConnectorRegistry().get_manifest("microsoft_365")
    assert m.implemented is True
    assert m.maturity in ("experimental", "beta", "stable")
    assert "users" in m.capabilities
    assert "oauth2" in m.auth_modes


def test_m365_connection_redacts_secret_and_syncs_postures(client, db_session: Session):
    tenant = _tenant(db_session, "m365-a")
    admin = create_user_with_membership(db_session, "m365-a@example.com", "tenant_admin", tenant)
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Northwind M365",
        status="active",
        owner_name="Owner",
        demo_profile={
            "microsoft_365": {
                "licensed_users": 40,
                "active_sign_ins_30d": 31,
                "unused_licences": 5,
                "mfa_coverage_pct": 72,
                "hygiene": "Shared account hygiene issues noted.",
            }
        },
    )
    db_session.add(customer)
    db_session.commit()

    create = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers(admin, str(tenant.id)),
        json={
            "system_type": "microsoft_365",
            "display_name": "M365 demo",
            "auth_mode": "oauth2",
            "sync_cadence_minutes": 60,
            "config": {"tenant_id": "t", "client_id": "c", "client_secret": "secret", "demo_mode": True},
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["safe_config"]["client_secret"] == "[redacted]"
    cid = create.json()["id"]

    sync = client.post(f"/api/v1/integrations/connections/{cid}/sync", headers=auth_headers(admin, str(tenant.id)))
    assert sync.status_code == 202, sync.text
    assert sync.json()["status"] == "succeeded"

    posture = db_session.scalars(select(M365CustomerPosture).where(M365CustomerPosture.tenant_id == tenant.id)).first()
    assert posture is not None
    assert posture.customer_id == customer.id
    assert posture.active_users_30d == 31

    mappings = db_session.scalars(
        select(SourceEntityMapping).where(
            SourceEntityMapping.tenant_id == tenant.id, SourceEntityMapping.entity_type == "m365_customer_posture"
        )
    ).all()
    assert len(mappings) >= 1


def test_m365_workspace_and_customer_detail_shapes(client, db_session: Session):
    tenant = _tenant(db_session, "m365-b")
    admin = create_user_with_membership(db_session, "m365-b@example.com", "tenant_admin", tenant)
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="B Customer",
        status="watch",
        owner_name="Owner",
        demo_profile={"microsoft_365": {"licensed_users": 20, "active_sign_ins_30d": 12, "unused_licences": 4}},
    )
    db_session.add(customer)
    db_session.commit()

    conn = SourceSystemConnection(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        system_type="microsoft_365",
        provider_family="microsoft_365",
        display_name="M365",
        auth_mode="oauth2",
        encrypted_config=None,
        status="connected",
        health_status="healthy",
        is_enabled=True,
        sync_cadence_minutes=60,
        sync_mode="manual_and_scheduled",
        connector_version="m365_v1",
        connection_metadata={},
    )
    db_session.add(conn)
    db_session.flush()
    from app.services.m365_canonical import upsert_m365_for_customer

    upsert_m365_for_customer(
        db_session,
        tenant_id=tenant.id,
        customer_id=customer.id,
        demo_profile=customer.demo_profile,
        source_connection_id=conn.id,
        provenance="test",
    )
    db_session.commit()

    ws = client.get("/api/v1/workspace/m365-health", headers=auth_headers(admin, str(tenant.id)))
    assert ws.status_code == 200, ws.text
    body = ws.json()
    assert body["summary"]["linked_count"] == 1
    assert body["customers"][0]["customer_name"] == "B Customer"

    detail = client.get(f"/api/v1/customers/{customer.id}", headers=auth_headers(admin, str(tenant.id)))
    assert detail.status_code == 200, detail.text
    d = detail.json()
    assert d["m365"] is not None
    assert d["m365"]["linked"] is True


def test_billing_integrity_includes_m365_mismatch_signal(client, db_session: Session):
    tenant = _tenant(db_session, "m365-c")
    admin = create_user_with_membership(db_session, "m365-c@example.com", "tenant_admin", tenant)
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Mismatch Co",
        status="watch",
        owner_name="Owner",
        demo_profile={
            "billing": {"billed_m365_seats": 10, "active_mailboxes_measured": 10},
            "microsoft_365": {"licensed_users": 22, "active_sign_ins_30d": 21, "unused_licences": 1},
        },
    )
    db_session.add(customer)
    db_session.flush()
    from app.services.finance_canonical import upsert_finance_for_customer
    from app.services.m365_canonical import upsert_m365_for_customer

    upsert_finance_for_customer(
        db_session,
        tenant_id=tenant.id,
        customer_id=customer.id,
        customer_name=customer.name,
        demo_profile=customer.demo_profile,
        source_connection_id=None,
        provenance="test",
    )
    upsert_m365_for_customer(
        db_session,
        tenant_id=tenant.id,
        customer_id=customer.id,
        demo_profile=customer.demo_profile,
        source_connection_id=None,
        provenance="test",
    )
    db_session.commit()

    res = client.get("/api/v1/workspace/billing-integrity", headers=auth_headers(admin, str(tenant.id)))
    assert res.status_code == 200, res.text
    rows = res.json()["accounts"]
    assert rows and any("M365" in s for s in rows[0]["signals"])

