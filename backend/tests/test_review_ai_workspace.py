"""Review/QBR workspace APIs: context, artefacts, generation + persistence."""

import json
import uuid
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models.entities import (
    AIProvider,
    Customer,
    CustomerReviewAiArtifact,
    PromptDefinition,
    PromptVersion,
    Tenant,
    TenantAiSettings,
)
from app.domain.ai_constants import PROMPT_SCOPE_PLATFORM
from app.services.ai_providers.base import ChatCompletionResult
from app.services.review_qbr_context import build_review_qbr_variables
from tests.helpers import auth_headers, create_user_with_membership
from tests.test_ai_execution import _seed_min_tenant_ai


def _json_agenda():
    return {
        "meeting_title": "Quarterly review",
        "objectives": ["Align on priorities"],
        "agenda_sections": [{"title": "Intro", "duration_minutes": 5, "talking_points": ["Welcome"]}],
        "suggested_questions": [],
        "follow_up_actions": [],
        "confidence_notes": [],
        "short_context": {
            "summary": "Focused on hygiene",
            "key_points": ["M365"],
            "recommended_actions": [],
            "open_questions": [],
            "customer_safe_topics": ["Service review"],
            "internal_only_notes": [],
            "confidence_level": "medium",
            "missing_data": [],
        },
    }


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_review_agenda_post_persists_artifact(mock_chat, client, db_session: Session):
    payload = json.dumps(_json_agenda())
    mock_chat.return_value = ChatCompletionResult(text=payload, raw={"choices": [{"message": {"content": payload}}]})
    tenant = Tenant(id=uuid.uuid4(), slug="rv1", name="RV1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "rv1@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Acme Legal", status="active", owner_name="Pat")
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
    r = client.post(f"/api/v1/reviews/{cust.id}/ai/agenda", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "succeeded"
    assert body.get("artifact_id")
    assert body.get("structured_output", {}).get("meeting_title") == "Quarterly review"
    row = db_session.get(CustomerReviewAiArtifact, uuid.UUID(body["artifact_id"]))
    assert row is not None
    assert row.artifact_type == "review_agenda"
    assert row.short_context_json and row.short_context_json.get("summary")


def test_review_artifacts_list_and_latest(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="rv2", name="RV2", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "rv2@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Co", status="active", owner_name="o")
    db_session.add(cust)
    db_session.add(
        CustomerReviewAiArtifact(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=cust.id,
            artifact_type="review_agenda",
            title="Old",
            status="succeeded",
            full_output_json={"x": 1},
            short_context_json={"summary": "s"},
            created_by_user_id=admin.id,
        )
    )
    db_session.commit()
    h = auth_headers(admin, str(tenant.id))
    r = client.get(f"/api/v1/reviews/{cust.id}/ai/artifacts", headers=h)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    r2 = client.get(f"/api/v1/reviews/{cust.id}/ai/artifacts/latest", headers=h)
    assert r2.status_code == 200
    assert r2.json()["by_type"]["review_agenda"]["title"] == "Old"


def test_review_context_previous_summaries_roundtrip(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="rv3", name="RV3", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "rv3@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Beta", status="active", owner_name="o")
    db_session.add(cust)
    db_session.add(
        CustomerReviewAiArtifact(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=cust.id,
            artifact_type="review_agenda",
            title="T",
            status="succeeded",
            full_output_json={},
            short_context_json={"summary": "Prior agenda", "recommended_actions": ["A1"]},
            created_by_user_id=admin.id,
        )
    )
    db_session.commit()
    h = auth_headers(admin, str(tenant.id))
    r = client.get(f"/api/v1/reviews/{cust.id}/context", headers=h)
    assert r.status_code == 200
    prev = r.json().get("previous_ai_artifacts") or []
    assert any(p.get("summary") == "Prior agenda" for p in prev)
    vars_built = build_review_qbr_variables(
        db_session, tenant.id, cust.id, caller_name="Alex", caller_email="a@x.com", caller_role="tenant_admin"
    )
    assert any(x.get("summary") == "Prior agenda" for x in (vars_built.get("previous_ai_artifacts") or []))


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_placeholder_warning_on_agenda(mock_chat, client, db_session: Session):
    mock_chat.return_value = ChatCompletionResult(text="Hello [Customer Name] — agenda", raw={})
    tenant = Tenant(id=uuid.uuid4(), slug="rv4", name="RV4", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "rv4@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="RealCo", status="active", owner_name="o")
    db_session.add(cust)
    db_session.commit()
    prov = _seed_min_tenant_ai(
        db_session,
        tenant=tenant,
        user=admin,
        task_type="customer_review_agenda",
        prompt_key="customer_review_agenda.system",
    )
    from app.core.ai_settings_crypto import encrypt_settings_payload

    prov.encrypted_settings = encrypt_settings_payload({"api_key": "sk-test"})
    db_session.commit()
    h = auth_headers(admin, str(tenant.id))
    r = client.post(f"/api/v1/reviews/{cust.id}/ai/agenda", headers=h)
    assert r.status_code == 200
    warns = r.json().get("output_warnings") or []
    assert any("placeholder" in w.lower() for w in warns)


@patch("app.services.ai_execution_service.execute_chat_completion")
def test_review_email_post_succeeds_without_precreated_task_route(mock_chat, client, db_session: Session):
    """Regression: Review email must work before the tenant opens /app/ai-settings (stub route auto-created)."""
    payload = json.dumps(
        {
            "subject": "QBR scheduling — Acme",
            "body": "Hello,\n\nWe would like to schedule your quarterly review.\n\nRegards,\nMSP",
            "short_context": {"summary": "Scheduling note", "key_points": []},
        }
    )
    mock_chat.return_value = ChatCompletionResult(text=payload, raw={})
    tenant = Tenant(id=uuid.uuid4(), slug="rv5", name="RV5", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "rv5@example.com", "tenant_admin", tenant)
    cust = Customer(id=uuid.uuid4(), tenant_id=tenant.id, name="Acme", status="active", owner_name="Pat")
    db_session.add(cust)
    p = AIProvider(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        provider_name="openai-dev",
        status="configured",
        provider_family="openai",
        deployment_mode="hosted",
        display_label="OpenAI",
        is_enabled=True,
        encrypted_settings=None,
    )
    db_session.add(p)
    db_session.add(
        TenantAiSettings(
            tenant_id=tenant.id,
            default_ai_provider_id=p.id,
            default_model="gpt-4o-mini",
            fallback_ai_provider_id=None,
            fallback_model=None,
            extra=None,
            updated_by_user_id=admin.id,
        )
    )
    d = PromptDefinition(
        id=uuid.uuid4(),
        scope=PROMPT_SCOPE_PLATFORM,
        tenant_id=None,
        prompt_key="customer_review_email_draft.system",
        title="Email",
        description=None,
        task_type="customer_review_email_draft",
        created_by_user_id=admin.id,
        updated_by_user_id=admin.id,
    )
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_definition_id=d.id,
        version_number=1,
        prompt_text="Draft email JSON only. Context: {{review_workspace}}",
        change_note=None,
        created_by_user_id=admin.id,
        is_active=True,
        version_metadata=None,
    )
    db_session.add_all([d, v])
    db_session.commit()
    from app.core.ai_settings_crypto import encrypt_settings_payload

    p.encrypted_settings = encrypt_settings_payload({"api_key": "sk-test"})
    db_session.commit()
    h = auth_headers(admin, str(tenant.id))
    r = client.post(f"/api/v1/reviews/{cust.id}/ai/email-draft?tone=professional", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "succeeded"
    assert body.get("structured_output", {}).get("subject") == "QBR scheduling — Acme"
    from app.repositories.tenant_ai_config import TenantAiConfigRepository

    tr = TenantAiConfigRepository(db_session).get_route_by_task(tenant.id, "customer_review_email_draft")
    assert tr is not None
