from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    ConnectorMappingReview,
    Customer,
    FinanceBillingAccount,
    FinanceBillingSnapshot,
    FinanceInvoice,
    FinanceInvoiceLine,
    SourceEntityMapping,
    SourceSystemConnection,
    Tenant,
)
from app.services.billing_integrity_service import BillingIntegrityService
from app.services.connectors.providers.xero import XeroConnectorAdapter
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


def test_xero_sync_writes_contacts_invoices_lines_and_mappings(monkeypatch, db_session: Session, client):
    tenant = _tenant(db_session, "fin-x")
    admin = create_user_with_membership(db_session, "fin-x@example.com", "tenant_admin", tenant)
    conn = SourceSystemConnection(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        system_type="xero",
        provider_family="xero",
        display_name="Xero",
        auth_mode="api_key",
        base_url="http://connector-lab:8099",
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
    )
    db_session.add(cust)
    db_session.commit()

    def fake_list_resource(self, *, base_url: str, path: str, headers: dict[str, str], since_cursor: str | None):
        if path == "/xero/contacts":
            return [
                {
                    "id": "X-C001",
                    "ContactID": "00000001-0001-0001-0001-000000000001",
                    "Name": "XeroCo",
                    "EmailAddress": "ops@xeroco.example",
                },
                {
                    "id": "X-C002",
                    "ContactID": "00000002-0002-0002-0002-000000000002",
                    "Name": "Unmapped Co",
                },
            ]
        if path == "/xero/invoices":
            return [
                {
                    "id": "X-I001",
                    "InvoiceID": "11111111-1111-1111-1111-111111111111",
                    "Contact": {"ContactID": "00000001-0001-0001-0001-000000000001"},
                    "Status": "AUTHORISED",
                    "Total": 1200,
                    "AmountDue": 500,
                    "Date": "2026-04-01",
                    "DueDate": "2026-04-15",
                }
            ]
        if path == "/xero/invoice-lines":
            return [
                {
                    "id": "X-L001",
                    "invoice_id": "X-I001",
                    "description": "Managed support",
                    "qty": 1,
                    "unit_amount": 1200,
                    "tax_amount": 200,
                    "line_total": 1200,
                    "account_code": "200",
                }
            ]
        return []

    monkeypatch.setattr(XeroConnectorAdapter, "_list_resource", fake_list_resource)

    from app.core.ai_settings_crypto import encrypt_settings_payload

    conn.encrypted_config = encrypt_settings_payload(
        {
            "api_key": "connector-lab-api-key",
            "xero_tenant_id": "demo-tenant-id",
        }
    )
    db_session.add(
        SourceEntityMapping(
            tenant_id=tenant.id,
            source_connection_id=conn.id,
            entity_type="customer",
            source_id="00000001-0001-0001-0001-000000000001",
            canonical_entity_id=cust.id,
        )
    )
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
    assert stats.get("finance_invoices_upserted", 0) >= 1

    accounts = db_session.scalars(select(FinanceBillingAccount).where(FinanceBillingAccount.tenant_id == tenant.id)).all()
    assert len(accounts) >= 1
    invoices = db_session.scalars(select(FinanceInvoice).where(FinanceInvoice.tenant_id == tenant.id)).all()
    assert len(invoices) >= 1
    lines = db_session.scalars(select(FinanceInvoiceLine).where(FinanceInvoiceLine.tenant_id == tenant.id)).all()
    assert len(lines) >= 1

    first_line_count = len(lines)
    r2 = client.post(
        f"/api/v1/integrations/connections/{conn.id}/sync",
        headers=auth_headers(admin, str(tenant.id)),
    )
    assert r2.status_code == 202, r2.text
    lines_after = db_session.scalars(select(FinanceInvoiceLine).where(FinanceInvoiceLine.tenant_id == tenant.id)).all()
    assert len(lines_after) == first_line_count

    reviews = db_session.scalars(
        select(ConnectorMappingReview).where(ConnectorMappingReview.tenant_id == tenant.id)
    ).all()
    assert len(reviews) >= 1


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


def test_xero_sync_respects_tenant_boundary(monkeypatch, db_session: Session, client):
    ta = _tenant(db_session, "xero-a")
    tb = _tenant(db_session, "xero-b")
    aa = create_user_with_membership(db_session, "xero-a@example.com", "tenant_admin", ta)
    create_user_with_membership(db_session, "xero-b@example.com", "tenant_admin", tb)

    from app.core.ai_settings_crypto import encrypt_settings_payload

    conn_a = SourceSystemConnection(
        id=uuid.uuid4(),
        tenant_id=ta.id,
        system_type="xero",
        provider_family="xero",
        display_name="XA",
        auth_mode="api_key",
        base_url="http://connector-lab:8099",
        status="disconnected",
        is_enabled=True,
        health_status="unknown",
        sync_mode="manual_and_scheduled",
        sync_cadence_minutes=120,
        connector_version="finance_v1",
        encrypted_config=encrypt_settings_payload({"api_key": "connector-lab-api-key", "xero_tenant_id": "demo-tenant-id"}),
    )
    db_session.add(conn_a)
    db_session.commit()

    def fake_list_resource(self, *, base_url: str, path: str, headers: dict[str, str], since_cursor: str | None):
        if path == "/xero/contacts":
            return [{"id": "X-CA", "ContactID": "CROSS-A", "Name": "Cross Tenant A"}]
        if path == "/xero/invoices":
            return [
                {
                    "id": "X-IA",
                    "InvoiceID": "INV-A",
                    "Contact": {"ContactID": "CROSS-A"},
                    "Status": "AUTHORISED",
                    "Total": 100,
                    "AmountDue": 100,
                }
            ]
        if path == "/xero/invoice-lines":
            return [{"id": "X-LA", "invoice_id": "X-IA", "description": "Line", "qty": 1, "unit_amount": 100}]
        return []

    monkeypatch.setattr(XeroConnectorAdapter, "_list_resource", fake_list_resource)

    run = client.post(f"/api/v1/integrations/connections/{conn_a.id}/sync", headers=auth_headers(aa, str(ta.id)))
    assert run.status_code == 202
    a_invoices = db_session.scalars(select(FinanceInvoice).where(FinanceInvoice.tenant_id == ta.id)).all()
    b_invoices = db_session.scalars(select(FinanceInvoice).where(FinanceInvoice.tenant_id == tb.id)).all()
    assert len(a_invoices) > 0
    assert len(b_invoices) == 0


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
    assert "total_invoice_count" in fin
    assert "recent_invoice_lines" in fin
