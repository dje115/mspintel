from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Customer,
    FinanceBillingAccount,
    FinanceBillingSnapshot,
    FinanceInvoice,
    SourceSystemConnection,
    Tenant,
)
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.finance_canonical import upsert_finance_for_customer
from tests.helpers import auth_headers, create_user_with_membership


def _tenant(db: Session, slug: str) -> Tenant:
    t = Tenant(id=uuid.uuid4(), slug=slug, name=slug, is_active=True)
    db.add(t)
    db.commit()
    return t


def test_upsert_finance_canonical_from_demo_profile(db_session: Session):
    tenant = _tenant(db_session, "fin-a")
    cust = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="TestCo",
        status="active",
        demo_profile={
            "synthetic": True,
            "billing": {
                "billed_m365_seats": 10,
                "active_mailboxes_measured": 14,
                "storage_tb_billed": 2,
                "aged_debt_gbp": 0,
                "invoice_friction": "none",
            },
            "microsoft_365": {"licensed_users": 16},
            "data_quality": {"confidence": "high"},
        },
    )
    db_session.add(cust)
    db_session.commit()
    upsert_finance_for_customer(
        db_session,
        tenant_id=tenant.id,
        customer_id=cust.id,
        customer_name=cust.name,
        demo_profile=cust.demo_profile,
        source_connection_id=None,
        provenance="test",
    )
    db_session.commit()
    acct = db_session.scalars(select(FinanceBillingAccount).where(FinanceBillingAccount.tenant_id == tenant.id)).one()
    assert acct.customer_id == cust.id
    snaps = db_session.scalars(select(FinanceBillingSnapshot).where(FinanceBillingSnapshot.billing_account_id == acct.id)).all()
    assert len(snaps) >= 1
    assert snaps[0].effective_date == date.today()
    invs = db_session.scalars(select(FinanceInvoice).where(FinanceInvoice.billing_account_id == acct.id)).all()
    assert len(invs) >= 2


def test_billing_integrity_underbilling_signal(db_session: Session):
    tenant = _tenant(db_session, "fin-b")
    cust = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="UnderCo",
        status="active",
        demo_profile={
            "billing": {"billed_m365_seats": 5, "active_mailboxes_measured": 20, "invoice_friction": "none"},
            "microsoft_365": {"licensed_users": 22},
            "data_quality": {"confidence": "medium"},
        },
    )
    db_session.add(cust)
    db_session.commit()
    upsert_finance_for_customer(
        db_session,
        tenant_id=tenant.id,
        customer_id=cust.id,
        customer_name=cust.name,
        demo_profile=cust.demo_profile,
        source_connection_id=None,
        provenance="test",
    )
    db_session.commit()
    ws = BillingIntegrityService(db_session).build_workspace(tenant.id)
    assert ws["summary"]["underbilling_candidate_count"] >= 1
    row = next(r for r in ws["accounts"] if r["customer_id"] == cust.id)
    assert row["finance_linked"] is True
    assert any("underbilling" in s.lower() or "exceed" in s.lower() for s in row["signals"])


def test_xero_demo_sync_writes_mappings(db_session: Session, client):
    tenant = _tenant(db_session, "fin-x")
    admin = create_user_with_membership(db_session, "fin-x@example.com", "tenant_admin", tenant)
    conn = SourceSystemConnection(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        system_type="xero",
        provider_family="xero",
        display_name="Xero",
        auth_mode="sandbox",
        status="disconnected",
        is_enabled=True,
        health_status="unknown",
        sync_mode="manual_and_scheduled",
        sync_cadence_minutes=120,
        connector_version="finance_v0",
        encrypted_config=None,
    )
    db_session.add(conn)
    cust = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="XeroCo",
        status="active",
        demo_profile={"billing": {"billed_m365_seats": 3, "active_mailboxes_measured": 3, "invoice_friction": "none"}},
    )
    db_session.add(cust)
    db_session.commit()

    from app.core.ai_settings_crypto import encrypt_settings_payload

    conn.encrypted_config = encrypt_settings_payload({"demo_mode": True})
    db_session.commit()

    r = client.post(
        f"/api/v1/integrations/connections/{conn.id}/sync",
        headers=auth_headers(admin, str(tenant.id)),
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "succeeded"
    stats = body["stats_json"] or {}
    assert stats.get("finance_billing_accounts_upserted", 0) >= 1


def test_xero_safe_config_redacts_refresh_token(client, db_session: Session):
    tenant = _tenant(db_session, "fin-z")
    admin = create_user_with_membership(db_session, "fin-z@example.com", "tenant_admin", tenant)
    from app.core.ai_settings_crypto import encrypt_settings_payload

    payload = {
        "system_type": "xero",
        "display_name": "Z",
        "auth_mode": "oauth",
        "is_enabled": True,
        "sync_cadence_minutes": 120,
        "config": {
            "client_id": "public",
            "client_secret": "topsecret",
            "refresh_token": "never-leak",
            "xero_tenant_id": "111",
            "demo_mode": False,
        },
    }
    r = client.post("/api/v1/integrations/connections", headers=auth_headers(admin, str(tenant.id)), json=payload)
    assert r.status_code == 201, r.text
    sc = r.json()["safe_config"] or {}
    assert sc.get("client_secret") == "[redacted]"
    assert sc.get("refresh_token") == "[redacted]"
    assert "never-leak" not in str(r.json())


def test_billing_integrity_api_tenant_isolation(client, db_session: Session):
    ta = _tenant(db_session, "iso-a")
    tb = _tenant(db_session, "iso-b")
    aa = create_user_with_membership(db_session, "iso-a@example.com", "tenant_admin", ta)
    create_user_with_membership(db_session, "iso-b@example.com", "tenant_admin", tb)
    ca = Customer(id=uuid.uuid4(), tenant_id=ta.id, name="OnlyA", status="active", demo_profile={"billing": {"billed_m365_seats": 1, "active_mailboxes_measured": 1}})
    db_session.add(ca)
    db_session.commit()
    upsert_finance_for_customer(
        db_session,
        tenant_id=ta.id,
        customer_id=ca.id,
        customer_name=ca.name,
        demo_profile=ca.demo_profile,
        source_connection_id=None,
        provenance="test",
    )
    db_session.commit()

    r = client.get("/api/v1/workspace/billing-integrity", headers=auth_headers(aa, str(ta.id)))
    assert r.status_code == 200
    assert r.json()["summary"]["customer_count"] == 1


def test_customer_detail_finance_shape(client, db_session: Session):
    tenant = _tenant(db_session, "fin-cust")
    admin = create_user_with_membership(db_session, "fin-cust@example.com", "tenant_admin", tenant)
    cust = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="ShapeCo",
        status="active",
        demo_profile={"billing": {"billed_m365_seats": 8, "active_mailboxes_measured": 8, "invoice_friction": "none"}},
    )
    db_session.add(cust)
    db_session.commit()
    upsert_finance_for_customer(
        db_session,
        tenant_id=tenant.id,
        customer_id=cust.id,
        customer_name=cust.name,
        demo_profile=cust.demo_profile,
        source_connection_id=None,
        provenance="test",
    )
    db_session.commit()
    r = client.get(f"/api/v1/customers/{cust.id}", headers=auth_headers(admin, str(tenant.id)))
    assert r.status_code == 200
    fin = r.json().get("finance")
    assert fin is not None
    assert fin["finance_linked"] is True
    assert "integrity_highlights" in fin
