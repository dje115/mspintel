import uuid

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.domain.ai_constants import AI_TASK_TYPES, PROMPT_SCOPE_PLATFORM
from app.models.entities import AITaskRun, AIProvider, PromptDefinition, PromptVersion, Tenant, User
from app.services.ai_runtime_resolver import AIRuntimeResolver
from tests.helpers import auth_headers, create_platform_admin, create_user_with_membership, platform_auth_headers


def test_tenant_ai_settings_patch_merges(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ai-set", name="AI Set", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ai-set@example.com", "tenant_admin", tenant)
    prov = AIProvider(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        provider_name="openai",
        status="configured",
        provider_family="openai",
        deployment_mode="hosted",
        is_enabled=True,
    )
    db_session.add(prov)
    db_session.commit()

    h = auth_headers(admin, str(tenant.id))
    r0 = client.get("/api/v1/ai/settings", headers=h)
    assert r0.status_code == 200

    r1 = client.patch(
        "/api/v1/ai/settings",
        headers=h,
        json={"default_ai_provider_id": str(prov.id), "default_model": "gpt-first"},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["default_model"] == "gpt-first"

    r2 = client.patch("/api/v1/ai/settings", headers=h, json={"default_model": "gpt-second"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["default_model"] == "gpt-second"
    assert r2.json()["default_ai_provider"]["id"] == str(prov.id)


def test_task_routes_and_resolve_use_platform_prompt(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ai-tr", name="AI TR", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ai-tr@example.com", "tenant_admin", tenant)
    plat = create_platform_admin(db_session, "plat-tr@example.com")

    d = PromptDefinition(
        id=uuid.uuid4(),
        scope=PROMPT_SCOPE_PLATFORM,
        tenant_id=None,
        prompt_key="ticket_triage.system",
        title="TT",
        description=None,
        task_type="ticket_triage",
        created_by_user_id=plat.id,
        updated_by_user_id=plat.id,
    )
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_definition_id=d.id,
        version_number=1,
        prompt_text="You are the platform triage bot.",
        change_note="seed",
        created_by_user_id=plat.id,
        is_active=True,
        version_metadata=None,
    )
    db_session.add_all([d, v])
    db_session.commit()

    h = auth_headers(admin, str(tenant.id))
    routes = client.get("/api/v1/ai/task-routes", headers=h)
    assert routes.status_code == 200
    assert len(routes.json()) == len(AI_TASK_TYPES)

    res = client.get("/api/v1/ai/resolve/ticket_triage", headers=h)
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is True
    assert body["prompt_key"] == "ticket_triage.system"
    assert body["prompt_text"] == "You are the platform triage bot."


def test_tenant_prompt_override_and_activate(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ai-po", name="AI PO", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ai-po@example.com", "tenant_admin", tenant)
    plat = create_platform_admin(db_session, "plat-po@example.com")

    d = PromptDefinition(
        id=uuid.uuid4(),
        scope=PROMPT_SCOPE_PLATFORM,
        tenant_id=None,
        prompt_key="email_draft.system",
        title="ED",
        description=None,
        task_type="email_draft",
        created_by_user_id=plat.id,
        updated_by_user_id=plat.id,
    )
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_definition_id=d.id,
        version_number=1,
        prompt_text="platform email",
        change_note=None,
        created_by_user_id=plat.id,
        is_active=True,
        version_metadata=None,
    )
    db_session.add_all([d, v])
    db_session.commit()

    h = auth_headers(admin, str(tenant.id))
    assert client.get("/api/v1/ai/task-routes", headers=h).status_code == 200

    ov = client.post(
        "/api/v1/prompts/tenant-overrides",
        headers=h,
        json={
            "prompt_key": "email_draft.system",
            "title": "Tenant email",
            "task_type": "email_draft",
            "initial_version": {"prompt_text": "tenant v1", "change_note": "first"},
        },
    )
    assert ov.status_code == 200, ov.text
    defn_id = ov.json()["definition_id"]

    res = client.get(f"/api/v1/ai/resolve/email_draft", headers=h)
    assert res.status_code == 200
    assert res.json()["prompt_text"] == "tenant v1"

    v2 = client.post(
        f"/api/v1/prompts/{defn_id}/versions",
        headers=h,
        json={"prompt_text": "tenant v2", "change_note": "second"},
    )
    assert v2.status_code == 200
    vid2 = next(x["id"] for x in v2.json()["versions"] if x["version_number"] == 2)

    act = client.post(f"/api/v1/prompts/{defn_id}/activate/{vid2}", headers=h)
    assert act.status_code == 200
    assert act.json()["active_version"]["version_number"] == 2

    res2 = client.get("/api/v1/ai/resolve/email_draft", headers=h)
    assert res2.json()["prompt_text"] == "tenant v2"

    rv = client.post("/api/v1/prompts/revert-to-default", headers=h, json={"prompt_key": "email_draft.system"})
    assert rv.status_code == 200

    res3 = client.get("/api/v1/ai/resolve/email_draft", headers=h)
    assert res3.json()["prompt_text"] == "platform email"


def test_prompt_configure_requires_permission(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ai-perm", name="AI Perm", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    viewer = create_user_with_membership(db_session, "ai-view@example.com", "director", tenant)
    plat = create_platform_admin(db_session, "plat-perm@example.com")
    d = PromptDefinition(
        id=uuid.uuid4(),
        scope=PROMPT_SCOPE_PLATFORM,
        tenant_id=None,
        prompt_key="risk_summary.system",
        title="RS",
        description=None,
        task_type="risk_summary",
        created_by_user_id=plat.id,
        updated_by_user_id=plat.id,
    )
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_definition_id=d.id,
        version_number=1,
        prompt_text="x",
        change_note=None,
        created_by_user_id=plat.id,
        is_active=True,
        version_metadata=None,
    )
    db_session.add_all([d, v])
    db_session.commit()

    h = auth_headers(viewer, str(tenant.id))
    denied = client.post(
        "/api/v1/prompts/tenant-overrides",
        headers=h,
        json={
            "prompt_key": "risk_summary.system",
            "title": "t",
            "task_type": "risk_summary",
            "initial_version": {"prompt_text": "nope"},
        },
    )
    assert denied.status_code == 403


def test_platform_prompt_create_version_activate(client, db_session: Session):
    plat = create_platform_admin(db_session, "plat-pc@example.com")
    ph = platform_auth_headers(plat)

    created = client.post(
        "/api/v1/platform/prompts",
        headers=ph,
        json={
            "prompt_key": "opportunity_detection.system",
            "title": "Opp",
            "task_type": "opportunity_detection",
            "description": "d",
            "initial_version": {"prompt_text": "v1 body", "change_note": "init"},
        },
    )
    if created.status_code == 409:
        # Already present from a previous test DB state; list and skip create.
        listed = client.get("/api/v1/platform/prompts", headers=ph)
        assert listed.status_code == 200
        defs = [x for x in listed.json() if x["prompt_key"] == "opportunity_detection.system"]
        assert defs
        defn_id = defs[0]["definition_id"]
    else:
        assert created.status_code == 200, created.text
        defn_id = created.json()["definition_id"]

    add_v = client.post(
        f"/api/v1/platform/prompts/{defn_id}/versions",
        headers=ph,
        json={"prompt_text": "v2 platform", "change_note": "next"},
    )
    assert add_v.status_code == 200
    vid = next(x["id"] for x in add_v.json()["versions"] if x["version_number"] == 2)

    act = client.post(f"/api/v1/platform/prompts/{defn_id}/activate/{vid}", headers=ph)
    assert act.status_code == 200
    assert act.json()["active_version"]["version_number"] == 2


def test_platform_catalog_requires_platform_session(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ai-cat", name="AI Cat", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "ai-cat@example.com", "tenant_admin", tenant)
    bad = client.get("/api/v1/platform/ai/providers/catalog", headers=auth_headers(user, str(tenant.id)))
    assert bad.status_code == 403


def test_record_task_run_lineage(db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ai-run", name="AI Run", is_active=True)
    db_session.add(tenant)
    user = User(
        id=uuid.uuid4(),
        email="run@example.com",
        full_name="Run",
        password_hash=get_password_hash("RunPass123!"),
        is_platform_admin=True,
    )
    db_session.add(user)
    db_session.commit()

    d = PromptDefinition(
        id=uuid.uuid4(),
        scope=PROMPT_SCOPE_PLATFORM,
        tenant_id=None,
        prompt_key="account_summary.system",
        title="AS",
        description=None,
        task_type="account_summary",
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_definition_id=d.id,
        version_number=1,
        prompt_text="sum",
        change_note=None,
        created_by_user_id=user.id,
        is_active=True,
        version_metadata=None,
    )
    db_session.add_all([d, v])
    prov = AIProvider(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        provider_name="ollama",
        status="configured",
        provider_family="ollama",
        deployment_mode="local",
        is_enabled=True,
    )
    db_session.add(prov)
    from app.models.entities import TenantAiTaskRoute

    tr = TenantAiTaskRoute(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        task_type="account_summary",
        ai_provider_id=prov.id,
        model="llama",
        fallback_ai_provider_id=None,
        fallback_model=None,
        prompt_key="account_summary.system",
        enabled=True,
    )
    run = AITaskRun(id=uuid.uuid4(), tenant_id=tenant.id, task_type="account_summary", status="queued")
    db_session.add_all([tr, run])
    db_session.commit()

    r = AIRuntimeResolver(db_session).resolve(tenant.id, "account_summary")
    AIRuntimeResolver(db_session).record_task_run_lineage(
        run_id=run.id,
        tenant_id=tenant.id,
        resolved=r,
        status="succeeded",
        duration_ms=12,
        run_metadata={"k": "v"},
    )
    db_session.commit()
    db_session.refresh(run)
    assert run.provider_family == "ollama"
    assert run.deployment_mode == "local"
    assert run.model_used == "llama"
    assert run.ai_provider_id == prov.id
    assert run.prompt_definition_id == d.id
    assert run.prompt_version_id == v.id
    assert run.status == "succeeded"
    assert run.duration_ms == 12
    assert run.run_metadata == {"k": "v"}


def test_tenant_ai_provider_patch_and_delete(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ai-prov", name="AI Prov", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ai-prov@example.com", "tenant_admin", tenant)
    h = auth_headers(admin, str(tenant.id))

    created = client.post(
        "/api/v1/ai/providers",
        headers=h,
        json={
            "provider_family": "openai_compatible",
            "deployment_mode": "self_hosted",
            "display_label": "Lab Gateway",
            "base_url": "http://localhost:11434/v1",
            "settings": {"api_key": "local-secret", "model": "llama3.1"},
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["has_encrypted_settings"] is True
    provider_id = body["id"]

    patched = client.patch(
        f"/api/v1/ai/providers/{provider_id}",
        headers=h,
        json={
            "display_label": "Lab Gateway 2",
            "is_enabled": False,
            "settings": {"api_key": "rotated-secret", "model": "llama3.2"},
        },
    )
    assert patched.status_code == 200, patched.text
    pbody = patched.json()
    assert pbody["display_label"] == "Lab Gateway 2"
    assert pbody["is_enabled"] is False
    assert pbody["has_encrypted_settings"] is True

    listed = client.get("/api/v1/ai/providers", headers=h)
    assert listed.status_code == 200
    assert all("rotated-secret" not in str(row) for row in listed.json())

    deleted = client.delete(f"/api/v1/ai/providers/{provider_id}", headers=h)
    assert deleted.status_code == 204
    listed_after = client.get("/api/v1/ai/providers", headers=h)
    assert listed_after.status_code == 200
    assert all(row["id"] != provider_id for row in listed_after.json())
