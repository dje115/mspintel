import uuid
from unittest.mock import patch

from app.core.ai_settings_crypto import encrypt_settings_payload
from app.domain.ai_constants import PROMPT_SCOPE_PLATFORM
from app.models.entities import (
    AIProvider,
    Contact,
    Customer,
    M365CustomerPosture,
    PromptDefinition,
    PromptVersion,
    Recommendation,
    Tenant,
    TenantAiTaskRoute,
    Ticket,
)
from app.services.ai_providers.base import ChatCompletionResult, ProviderTransportError
from tests.helpers import auth_headers, create_user_with_membership


def _seed_m365_workspace_ai_route(db_session, tenant: Tenant, user, *, task_type: str, prompt_key: str):
    provider = AIProvider(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        provider_name="provider",
        status="configured",
        provider_family="openai",
        deployment_mode="hosted",
        display_label="OpenAI",
        is_enabled=True,
        encrypted_settings=encrypt_settings_payload({"api_key": "sk-test"}),
    )
    prompt_def = PromptDefinition(
        id=uuid.uuid4(),
        scope=PROMPT_SCOPE_PLATFORM,
        tenant_id=None,
        prompt_key=prompt_key,
        title="m365 prompt",
        description=None,
        task_type=task_type,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    prompt_ver = PromptVersion(
        id=uuid.uuid4(),
        prompt_definition_id=prompt_def.id,
        version_number=1,
        prompt_text="Summarize portfolio M365 posture: {{portfolio_context}}",
        change_note="test",
        created_by_user_id=user.id,
        is_active=True,
        version_metadata=None,
    )
    route = TenantAiTaskRoute(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        task_type=task_type,
        ai_provider_id=provider.id,
        model="gpt-4o-mini",
        fallback_ai_provider_id=None,
        fallback_model=None,
        prompt_key=prompt_key,
        enabled=True,
    )
    db_session.add_all([provider, prompt_def, prompt_ver, route])
    db_session.commit()


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


def test_m365_workspace_ai_summary_requires_linked_data(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="m365-no-data", name="M365 No Data", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "m365-no-data@example.com", "tenant_admin", tenant)
    _seed_m365_workspace_ai_route(
        db_session,
        tenant,
        user,
        task_type="m365_hygiene_summary",
        prompt_key="m365_hygiene_summary.system",
    )
    res = client.post("/api/v1/workspace/m365-health/ai/summary", headers=auth_headers(user, str(tenant.id)))
    assert res.status_code == 400
    assert "No linked Microsoft 365 posture rows" in res.json()["detail"]


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_m365_workspace_ai_summary_generates_and_reads_latest(mock_chat, client, db_session):
    mock_chat.return_value = ChatCompletionResult(
        text="## Executive summary\nPortfolio hygiene is mixed.",
        raw={"choices": [{"message": {"content": "ok"}}]},
    )
    tenant = Tenant(id=uuid.uuid4(), slug="m365-ai", name="M365 AI", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "m365-ai@example.com", "tenant_admin", tenant)
    customer = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Acme", status="active", owner_name="Owner")
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        M365CustomerPosture(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=customer.id,
            confidence_level="medium",
            licensed_users=20,
            active_users_30d=15,
            inactive_users_30d=5,
            disabled_users=1,
            stale_users_90d=3,
            mailbox_count=22,
            shared_mailbox_count=4,
            unused_licences=5,
            hygiene_findings=["Inactive users require cleanup."],
            optimisation_findings=["Unused licences can be optimised."],
        )
    )
    db_session.commit()
    _seed_m365_workspace_ai_route(
        db_session,
        tenant,
        user,
        task_type="m365_hygiene_summary",
        prompt_key="m365_hygiene_summary.system",
    )
    post = client.post("/api/v1/workspace/m365-health/ai/summary", headers=auth_headers(user, str(tenant.id)))
    assert post.status_code == 200, post.text
    assert post.json()["status"] == "succeeded"
    assert post.json()["prompt_version_id"] is not None

    latest = client.get("/api/v1/workspace/m365-health/ai/latest", headers=auth_headers(user, str(tenant.id)))
    assert latest.status_code == 200
    assert latest.json()["status"] == "succeeded"
    assert "Executive summary" in (latest.json().get("text") or "")
    user_payload = mock_chat.call_args.kwargs["user_content"]
    assert "portfolio_m365_workspace" in user_payload
    assert "portfolio-level totals across linked customers" in user_payload
    assert "top_customer_outliers" in user_payload


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_m365_workspace_ai_opportunity_provider_failure_is_safe(mock_chat, client, db_session):
    mock_chat.side_effect = ProviderTransportError("provider misconfigured")
    tenant = Tenant(id=uuid.uuid4(), slug="m365-ai-fail", name="M365 AI Fail", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "m365-ai-fail@example.com", "tenant_admin", tenant)
    customer = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Acme", status="active", owner_name="Owner")
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        M365CustomerPosture(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=customer.id,
            confidence_level="medium",
            licensed_users=10,
            active_users_30d=8,
            inactive_users_30d=2,
            mailbox_count=10,
        )
    )
    db_session.commit()
    _seed_m365_workspace_ai_route(
        db_session,
        tenant,
        user,
        task_type="m365_upsell_opportunity",
        prompt_key="m365_upsell_opportunity.system",
    )
    post = client.post("/api/v1/workspace/m365-health/ai/opportunity", headers=auth_headers(user, str(tenant.id)))
    assert post.status_code == 200, post.text
    assert post.json()["status"] == "failed"
    assert "Check AI settings" in (post.json().get("message") or "")


def test_customer_detail_includes_synced_contacts(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="cust-contacts", name="Cust Contacts", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "cust-contacts@example.com", "tenant_admin", tenant)
    customer = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Northwind", status="active", owner_name="AM")
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        Contact(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=customer.id,
            name="Mina Lopez",
            email="mina@northwind.test",
            external_ref="ATC-001",
        )
    )
    db_session.commit()
    res = client.get(f"/api/v1/customers/{customer.id}", headers=auth_headers(user, str(tenant.id)))
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["contacts"]) == 1
    assert body["contacts"][0]["name"] == "Mina Lopez"


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_account_manager_next_conversation_context_includes_contacts_and_tickets(mock_chat, client, db_session):
    mock_chat.return_value = ChatCompletionResult(
        text="Use stakeholder-led recovery talk track.",
        raw={"choices": [{"message": {"content": "ok"}}]},
    )
    tenant = Tenant(id=uuid.uuid4(), slug="am-ai", name="AM AI", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "am-ai@example.com", "tenant_admin", tenant)
    customer = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Contoso", status="active", owner_name="AM")
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        Contact(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=customer.id,
            name="Jordan Stakeholder",
            email="jordan@contoso.test",
            external_ref="ATC-777",
        )
    )
    db_session.add(
        Ticket(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=customer.id,
            status="open",
            subject="VPN outage",
            external_ref="ATT-777",
        )
    )
    db_session.commit()
    _seed_m365_workspace_ai_route(
        db_session,
        tenant,
        user,
        task_type="account_manager_next_conversation",
        prompt_key="account_manager_next_conversation.system",
    )
    post = client.post(
        f"/api/v1/customers/{customer.id}/ai/account-manager-next-conversation",
        headers=auth_headers(user, str(tenant.id)),
    )
    assert post.status_code == 200, post.text
    assert post.json()["status"] == "succeeded"
    user_payload = mock_chat.call_args.kwargs["user_content"]
    assert "Jordan Stakeholder" in user_payload
    assert "VPN outage" in user_payload
