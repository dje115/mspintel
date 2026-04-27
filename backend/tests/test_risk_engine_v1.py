from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.entities import Contact, Customer, FinanceBillingAccount, FinanceBillingSnapshot, Tenant, Ticket
from app.services.risk_engine_v1 import RiskEngineV1Service
from tests.helpers import auth_headers, create_user_with_membership


def _tenant(db_session, slug: str) -> Tenant:
    t = Tenant(id=uuid.uuid4(), slug=slug, name=slug, is_active=True)
    db_session.add(t)
    db_session.commit()
    return t


def test_risk_engine_generates_factors_and_scores(client, db_session):
    tenant = _tenant(db_session, "risk-a")
    user = create_user_with_membership(db_session, "risk-a@example.com", "tenant_admin", tenant)
    c = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Risky Co",
        status="active",
        owner_name=None,
        demo_profile={"relationship": {"last_qbr_days_ago": 300, "stakeholder_count": 1}},
    )
    db_session.add(c)
    db_session.flush()
    for i in range(7):
        db_session.add(
            Ticket(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                customer_id=c.id,
                status="open",
                subject=f"T-{i}",
                created_at=datetime.now(UTC) - timedelta(days=35 + i),
            )
        )
    db_session.add(Contact(id=uuid.uuid4(), tenant_id=tenant.id, customer_id=c.id, name="Only One", email="one@test.local"))
    acct = FinanceBillingAccount(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        customer_id=c.id,
        source_connection_id=None,
        external_billing_account_id=f"t:{c.id}",
        display_name="Risky billing",
        linkage_status="linked",
    )
    db_session.add(acct)
    db_session.flush()
    db_session.add(
        FinanceBillingSnapshot(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            billing_account_id=acct.id,
            source_connection_id=None,
            effective_date=datetime.now(UTC).date(),
            billed_users=10,
            billed_mailboxes=10,
            service_licensed_users=18,
            service_active_mailboxes=20,
            payment_status_summary="overdue_60_plus",
            aged_outstanding_cents=120000,
            confidence_level="medium",
        )
    )
    db_session.commit()

    rr = client.post("/api/v1/workspace/risk-engine/recompute", headers=auth_headers(user, str(tenant.id)))
    assert rr.status_code == 200, rr.text
    row = RiskEngineV1Service(db_session).latest_score_for_customer(tenant.id, c.id)
    assert row is not None
    assert row.risk_score >= 70
    assert row.attention_score >= 55
    assert row.risk_level in ("medium", "high")
    assert "high_ticket_volume" in (row.reason_codes or [])
    assert "billing_mismatch" in (row.reason_codes or [])
    assert "payment_friction" in (row.reason_codes or [])
    assert row.scoring_version == "risk_v1"
    assert row.confidence_level in ("medium", "low")


def test_risk_engine_handles_missing_data_low_confidence(db_session):
    tenant = _tenant(db_session, "risk-b")
    c = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Sparse Co", status="active", owner_name=None, demo_profile={})
    db_session.add(c)
    db_session.commit()
    score = RiskEngineV1Service(db_session).recompute_customer(tenant.id, c.id)
    db_session.commit()
    assert score.confidence_level in ("low", "medium")
    assert "no_finance_link" in (score.reason_codes or [])
    assert any("confidence" in n.lower() or "missing" in n.lower() for n in (score.coverage_notes or []))


def test_risk_queue_and_tenant_isolation(client, db_session):
    ta = _tenant(db_session, "risk-qa")
    tb = _tenant(db_session, "risk-qb")
    ua = create_user_with_membership(db_session, "risk-qa@example.com", "tenant_admin", ta)
    ub = create_user_with_membership(db_session, "risk-qb@example.com", "tenant_admin", tb)
    ca = Customer(id=uuid.uuid4(), tenant_id=ta.id, name="A", status="active", owner_name="A")
    cb = Customer(id=uuid.uuid4(), tenant_id=tb.id, name="B", status="active", owner_name="B")
    db_session.add_all([ca, cb])
    db_session.commit()

    RiskEngineV1Service(db_session).recompute_tenant(ta.id)
    RiskEngineV1Service(db_session).recompute_tenant(tb.id)
    db_session.commit()

    qa = client.get("/api/v1/workspace/risk-queue?mode=at_risk&page=1&page_size=20", headers=auth_headers(ua, str(ta.id)))
    assert qa.status_code == 200
    for item in qa.json()["items"]:
        assert item["customer_name"] != "B"

    denied = client.get("/api/v1/workspace/risk-queue?mode=attention", headers=auth_headers(ua, str(tb.id)))
    assert denied.status_code == 403
    assert ub is not None


def test_dashboard_uses_risk_scores(client, db_session):
    tenant = _tenant(db_session, "risk-dash")
    user = create_user_with_membership(db_session, "risk-dash@example.com", "tenant_admin", tenant)
    c = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Dash Co", status="active", owner_name="Owner")
    db_session.add(c)
    db_session.commit()
    RiskEngineV1Service(db_session).recompute_tenant(tenant.id)
    db_session.commit()
    res = client.get("/api/v1/dashboards/executive", headers=auth_headers(user, str(tenant.id)))
    assert res.status_code == 200
    body = res.json()
    assert "high_risk_customers" in body
    assert isinstance(body["high_risk_customers"], int)


def test_customer_detail_includes_risk_engine_payload(client, db_session):
    tenant = _tenant(db_session, "risk-cust")
    user = create_user_with_membership(db_session, "risk-cust@example.com", "tenant_admin", tenant)
    c = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Customer", status="active", owner_name="Owner")
    db_session.add(c)
    db_session.commit()
    RiskEngineV1Service(db_session).recompute_customer(tenant.id, c.id)
    db_session.commit()

    r = client.get(f"/api/v1/customers/{c.id}", headers=auth_headers(user, str(tenant.id)))
    assert r.status_code == 200
    payload = r.json()
    assert payload["risk_engine"] is not None
    assert payload["risk_engine"]["scoring_version"] == "risk_v1"
