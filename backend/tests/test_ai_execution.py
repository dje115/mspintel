import uuid
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.domain.ai_constants import AI_RUN_SKIPPED, AI_RUN_SUCCEEDED, AI_RUN_UNSUPPORTED
from app.models.entities import (
    AIProvider,
    Customer,
    PromptDefinition,
    PromptVersion,
    Tenant,
    TenantAiTaskRoute,
    User,
)
from app.domain.ai_constants import PROMPT_SCOPE_PLATFORM
from app.services.ai_execution_service import AIExecutionService
from sqlalchemy import select

from app.services.ai_providers.base import ChatCompletionResult
from tests.helpers import auth_headers, create_user_with_membership


def _seed_min_tenant_ai(
    db: Session,
    tenant: Tenant,
    user: User,
    *,
    provider_family: str = "openai",
    task_enabled: bool = True,
    task_type: str = "account_summary",
    prompt_key: str = "account_summary.system",
) -> AIProvider:
    p = AIProvider(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        provider_name="p",
        status="configured",
        provider_family=provider_family,
        deployment_mode="hosted",
        display_label="L",
        is_enabled=True,
        encrypted_settings=None,
    )
    db.add(p)
    d = PromptDefinition(
        id=uuid.uuid4(),
        scope=PROMPT_SCOPE_PLATFORM,
        tenant_id=None,
        prompt_key=prompt_key,
        title="t",
        description=None,
        task_type=task_type,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_definition_id=d.id,
        version_number=1,
        prompt_text="Summarize: {{customer}}",
        change_note=None,
        created_by_user_id=user.id,
        is_active=True,
        version_metadata=None,
    )
    db.add_all([d, v])
    tr = TenantAiTaskRoute(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        task_type=task_type,
        ai_provider_id=p.id,
        model="gpt-4o-mini",
        fallback_ai_provider_id=None,
        fallback_model=None,
        prompt_key=prompt_key,
        enabled=task_enabled,
    )
    db.add(tr)
    db.commit()
    return p


def test_execute_skipped_when_task_disabled(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ex1", name="E1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ex1@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="C", status="active", owner_name="o")
    db_session.add(cust)
    db_session.commit()
    _seed_min_tenant_ai(db_session, tenant=tenant, user=admin, task_enabled=False)
    h = auth_headers(admin, str(tenant.id))
    r = client.post(f"/api/v1/customers/{cust.id}/ai/account-summary", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == AI_RUN_SKIPPED


def test_execute_unsupported_provider_family(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ex2", name="E2", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ex2@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="C", status="active", owner_name="o")
    db_session.add(cust)
    db_session.commit()
    _seed_min_tenant_ai(db_session, tenant=tenant, user=admin, provider_family="anthropic")
    h = auth_headers(admin, str(tenant.id))
    r = client.post(f"/api/v1/customers/{cust.id}/ai/account-summary", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == AI_RUN_UNSUPPORTED


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_account_summary_execute_success(mock_chat, client, db_session: Session):
    mock_chat.return_value = ChatCompletionResult(text="**Summary** ok", raw={"choices": [{"message": {"content": "**Summary** ok"}}]})
    tenant = Tenant(id=uuid.uuid4(), slug="ex3", name="E3", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ex3@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Acme", status="active", owner_name="o")
    db_session.add(cust)
    db_session.commit()
    prov = _seed_min_tenant_ai(db_session, tenant=tenant, user=admin, provider_family="openai")
    from app.core.ai_settings_crypto import encrypt_settings_payload

    prov.encrypted_settings = encrypt_settings_payload({"api_key": "sk-test"})
    db_session.commit()
    h = auth_headers(admin, str(tenant.id))
    r = client.post(f"/api/v1/customers/{cust.id}/ai/account-summary", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == AI_RUN_SUCCEEDED
    assert "Summary" in (body.get("text") or "")
    mock_chat.assert_called_once()


def test_account_summary_wrong_tenant_forbidden(client, db_session: Session):
    ta = Tenant(id=uuid.uuid4(), slug="a", name="A", is_active=True)
    tb = Tenant(id=uuid.uuid4(), slug="b", name="B", is_active=True)
    db_session.add_all([ta, tb])
    db_session.commit()
    ua = create_user_with_membership(db_session, "a@x.com", "tenant_admin", ta)
    cust_b = Customer(id=uuid.uuid4(), tenant_id=tb.id, name="Cb", status="active", owner_name="o")
    db_session.add(cust_b)
    db_session.commit()
    h = auth_headers(ua, str(ta.id))
    r = client.post(f"/api/v1/customers/{cust_b.id}/ai/account-summary", headers=h)
    assert r.status_code == 404


def test_read_block_state_not_generated(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ex4", name="E4", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ex4@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="C", status="active", owner_name="o")
    db_session.add(cust)
    db_session.commit()
    h = auth_headers(admin, str(tenant.id))
    r = client.get(f"/api/v1/customers/{cust.id}/ai/account-summary", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "not_generated"


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_customer_review_agenda_execute_success(mock_chat, client, db_session: Session):
    mock_chat.return_value = ChatCompletionResult(
        text="## Agenda\n1. Opening\n2. Service review", raw={"choices": [{"message": {"content": "## Agenda"}}]}
    )
    tenant = Tenant(id=uuid.uuid4(), slug="ex-ag", name="E-Ag", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ex-ag@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="AgendaCo", status="active", owner_name="o")
    db_session.add(cust)
    db_session.commit()
    prov = _seed_min_tenant_ai(
        db_session,
        tenant=tenant,
        user=admin,
        provider_family="openai",
        task_type="customer_review_agenda",
        prompt_key="customer_review_agenda.system",
    )
    from app.core.ai_settings_crypto import encrypt_settings_payload

    prov.encrypted_settings = encrypt_settings_payload({"api_key": "sk-test"})
    db_session.commit()
    h = auth_headers(admin, str(tenant.id))
    r = client.post(f"/api/v1/customers/{cust.id}/ai/customer-review-agenda", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == AI_RUN_SUCCEEDED
    assert "Agenda" in (body.get("text") or "")
    mock_chat.assert_called_once()


def test_execution_service_respects_tenant_provider(db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ex5", name="E5", is_active=True)
    db_session.add(tenant)
    u = create_user_with_membership(db_session, "ex5@x.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="C", status="active", owner_name="o")
    db_session.add(cust)
    db_session.commit()
    _seed_min_tenant_ai(db_session, tenant=tenant, user=u, provider_family="openai")
    from app.core.ai_settings_crypto import encrypt_settings_payload

    prov = db_session.scalars(select(AIProvider).where(AIProvider.tenant_id == tenant.id)).one()
    prov.encrypted_settings = encrypt_settings_payload({"api_key": "k"})
    db_session.commit()
    with patch("app.services.ai_execution_service.execute_chat_completion") as m:
        m.return_value = ChatCompletionResult(text="ok", raw={})
        out = AIExecutionService(db_session).execute(
            tenant_id=tenant.id,
            task_type="account_summary",
            variables={"customer": {"name": "C"}},
            actor_user_id=u.id,
            customer_id=cust.id,
        )
    assert out.status == AI_RUN_SUCCEEDED
    assert m.called
