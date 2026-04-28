from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.entities import AuditEvent, Customer, Recommendation, Tenant, TenantMspProfile, TenantServiceCatalogEntry
from app.services.ai_product_context import build_recommendation_explanation_variables
from app.services.tenant_profile import build_tenant_ai_context
from tests.helpers import auth_headers, create_user_with_membership


def _tenant(db_session, slug: str) -> Tenant:
    t = Tenant(id=uuid.uuid4(), slug=slug, name=slug.upper(), is_active=True)
    db_session.add(t)
    db_session.commit()
    return t


def test_tenant_profile_and_catalog_put_get_are_tenant_scoped(client, db_session):
    ta = _tenant(db_session, "tpa")
    tb = _tenant(db_session, "tpb")
    ua = create_user_with_membership(db_session, "tpa-admin@example.com", "tenant_admin", ta)
    _ub = create_user_with_membership(db_session, "tpb-admin@example.com", "tenant_admin", tb)

    payload = {
        "legal_name": "Northbridge MSP Ltd",
        "brand_name": "Northbridge",
        "regions_served": ["UK", "EU"],
        "vertical_focus": ["Healthcare"],
        "team_size_band": "26-50",
        "customer_count_band": "101-250",
        "typical_customer_size_band": "20-200 users",
        "delivery_model": "fully_managed",
        "business_goals": ["retention", "margin"],
        "free_text_description": "We provide managed Microsoft, security, and advisory services.",
    }
    rp = client.put("/api/tenant/profile", headers=auth_headers(ua, str(ta.id)), json=payload)
    assert rp.status_code == 200, rp.text
    assert rp.json()["legal_name"] == "Northbridge MSP Ltd"

    cat = {
        "tenant_id": str(ta.id),
        "items": [
            {"service_key": "managed_support", "service_name": "Managed support", "is_selected": True, "is_custom": False, "sort_order": 0},
            {"service_key": "custom_fractional_ciso", "service_name": "Fractional CISO", "is_selected": True, "is_custom": True, "sort_order": 1},
        ],
    }
    rc = client.put("/api/tenant/service-catalogue", headers=auth_headers(ua, str(ta.id)), json=cat)
    assert rc.status_code == 200, rc.text
    assert len(rc.json()["items"]) == 2

    ga = client.get("/api/tenant/profile", headers=auth_headers(ua, str(ta.id)))
    assert ga.status_code == 200
    assert ga.json()["brand_name"] == "Northbridge"

    denied = client.get("/api/tenant/profile", headers=auth_headers(ua, str(tb.id)))
    assert denied.status_code == 403


def test_tenant_profile_defaults_and_ai_context(client, db_session):
    tenant = _tenant(db_session, "tpc")
    user = create_user_with_membership(db_session, "tpc-admin@example.com", "tenant_admin", tenant)

    g1 = client.get("/api/tenant/profile", headers=auth_headers(user, str(tenant.id)))
    assert g1.status_code == 200
    assert g1.json()["legal_name"] is None

    g2 = client.get("/api/tenant/service-catalogue", headers=auth_headers(user, str(tenant.id)))
    assert g2.status_code == 200
    assert len(g2.json()["items"]) >= 5

    ctx = build_tenant_ai_context(db_session, tenant.id)
    assert ctx.tenant_id == tenant.id
    assert ctx.data_confidence_notes


def test_tenant_profile_changes_create_audit_events(client, db_session):
    tenant = _tenant(db_session, "tpd")
    user = create_user_with_membership(db_session, "tpd-admin@example.com", "tenant_admin", tenant)

    client.put(
        "/api/tenant/profile",
        headers=auth_headers(user, str(tenant.id)),
        json={"legal_name": "Audit MSP", "regions_served": ["UK"], "vertical_focus": [], "business_goals": []},
    )
    client.put(
        "/api/tenant/service-catalogue",
        headers=auth_headers(user, str(tenant.id)),
        json={
            "tenant_id": str(tenant.id),
            "items": [{"service_key": "managed_support", "service_name": "Managed support", "is_selected": True, "is_custom": False, "sort_order": 0}],
        },
    )

    events = list(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.tenant_id == tenant.id,
                AuditEvent.event_type.in_(("tenant.profile.updated", "tenant.service_catalog.updated")),
            )
        ).all()
    )
    assert len(events) == 2

    profile = db_session.scalars(select(TenantMspProfile).where(TenantMspProfile.tenant_id == tenant.id)).first()
    assert profile is not None
    services = list(db_session.scalars(select(TenantServiceCatalogEntry).where(TenantServiceCatalogEntry.tenant_id == tenant.id)).all())
    assert len(services) == 1


def test_recommendation_ai_variables_include_tenant_profile_context(db_session):
    tenant = _tenant(db_session, "tpe")
    customer = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Northwind", status="active", owner_name="Owner")
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        customer_id=customer.id,
        scope="service",
        status="open",
        summary="Follow up on onboarding coverage",
    )
    db_session.add_all([customer, rec])
    db_session.commit()

    vars_payload = build_recommendation_explanation_variables(db_session, tenant.id, rec.id)
    assert vars_payload["recommendation"]["id"] == str(rec.id)
    assert vars_payload["recommendation"]["customer_name"] == "Northwind"
    assert "tenant_profile_context" in vars_payload
    assert vars_payload["tenant_profile_context"]["tenant_id"] == str(tenant.id)
    assert "selected_services" in vars_payload["tenant_profile_context"]

