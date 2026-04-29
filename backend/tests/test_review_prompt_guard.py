import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Customer, Tenant, TenantAiTaskRoute
from app.services.review_prompt_guard import assert_review_ai_task_prompt_available
from tests.helpers import create_user_with_membership


def test_missing_platform_prompt_raises_503(db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="rg1", name="RG1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "rg1@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="C", status="active", owner_name="o")
    db_session.add(cust)
    db_session.add(
        TenantAiTaskRoute(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            task_type="customer_review_email_draft",
            ai_provider_id=None,
            model=None,
            fallback_ai_provider_id=None,
            fallback_model=None,
            prompt_key="customer_review_email_draft.system",
            enabled=True,
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        assert_review_ai_task_prompt_available(db_session, tenant.id, "customer_review_email_draft")
    assert exc.value.status_code == 503
    assert "sync_platform_prompt_defaults" in (exc.value.detail or "")


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_email_placeholder_stores_quality_flag(mock_chat, client, db_session: Session):
    import json

    from app.services.ai_providers.base import ChatCompletionResult

    bad = {"subject": "Hi [Customer Name]", "body": "Test", "short_context": {"summary": "x"}}
    mock_chat.return_value = ChatCompletionResult(text=json.dumps(bad), raw={})
    tenant = Tenant(id=uuid.uuid4(), slug="rg2", name="RG2", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "rg2@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="RealCo", status="active", owner_name="o")
    db_session.add(cust)
    db_session.commit()
    from tests.test_ai_execution import _seed_min_tenant_ai

    prov = _seed_min_tenant_ai(
        db_session,
        tenant=tenant,
        user=admin,
        task_type="customer_review_email_draft",
        prompt_key="customer_review_email_draft.system",
    )
    from app.core.ai_settings_crypto import encrypt_settings_payload

    prov.encrypted_settings = encrypt_settings_payload({"api_key": "sk-test"})
    db_session.commit()
    from tests.helpers import auth_headers

    h = auth_headers(admin, str(tenant.id))
    r = client.post(f"/api/v1/reviews/{cust.id}/ai/email-draft?tone=professional", headers=h)
    assert r.status_code == 200
    body = r.json()
    warns = body.get("output_warnings") or []
    assert any("Needs review" in w for w in warns)
    sc = body.get("short_context") or {}
    assert sc.get("quality_flags", {}).get("needs_customer_review") is True
