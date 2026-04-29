"""sync_platform_prompt_catalog: idempotent platform upsert; tenant overrides untouched."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.ai_constants import PROMPT_SCOPE_PLATFORM, PROMPT_SCOPE_TENANT
from app.models.entities import PromptDefinition, PromptVersion, Tenant, User
from app.services.ai_foundation_seed import sync_platform_prompt_catalog
from tests.helpers import create_user_with_membership


def test_sync_platform_prompt_catalog_idempotent(db_session: Session):
    s1 = sync_platform_prompt_catalog(db_session)
    s2 = sync_platform_prompt_catalog(db_session)
    assert s2["definitions_created"] == 0
    assert s2["versions_created"] == 0
    assert s1["definitions_created"] >= 0


def test_sync_does_not_overwrite_tenant_prompt_version_text(db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ps1", name="PS1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    admin = create_user_with_membership(db_session, "ps1@example.com", "tenant_admin", tenant)
    sync_platform_prompt_catalog(db_session)

    platform_def = db_session.scalars(
        select(PromptDefinition).where(
            PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
            PromptDefinition.tenant_id.is_(None),
            PromptDefinition.prompt_key == "account_summary.system",
        )
    ).first()
    assert platform_def is not None

    custom = "TENANT_CUSTOM_PROMPT_BODY_SHOULD_NOT_CHANGE"
    tdef = PromptDefinition(
        id=uuid.uuid4(),
        scope=PROMPT_SCOPE_TENANT,
        tenant_id=tenant.id,
        prompt_key="account_summary.system",
        title="Tenant override",
        description=None,
        task_type="account_summary",
        created_by_user_id=admin.id,
        updated_by_user_id=admin.id,
    )
    tv = PromptVersion(
        id=uuid.uuid4(),
        prompt_definition_id=tdef.id,
        version_number=1,
        prompt_text=custom,
        change_note="tenant",
        created_by_user_id=admin.id,
        is_active=True,
        version_metadata=None,
    )
    db_session.add_all([tdef, tv])
    db_session.commit()

    sync_platform_prompt_catalog(db_session)

    row = db_session.scalars(
        select(PromptVersion).where(PromptVersion.prompt_definition_id == tdef.id, PromptVersion.is_active.is_(True))
    ).first()
    assert row is not None
    assert row.prompt_text == custom

    # Platform definition still exists and was not replaced by tenant row
    pv = db_session.scalars(
        select(PromptVersion).where(
            PromptVersion.prompt_definition_id == platform_def.id, PromptVersion.is_active.is_(True)
        )
    ).first()
    assert pv is not None
    assert custom not in (pv.prompt_text or "")


def test_repair_adds_active_version_when_platform_def_orphaned(db_session: Session):
    """Platform definition exists but no active version — repair path."""
    sync_platform_prompt_catalog(db_session)
    d = db_session.scalars(
        select(PromptDefinition).where(
            PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
            PromptDefinition.prompt_key == "risk_summary.system",
        )
    ).one()
    for v in db_session.scalars(select(PromptVersion).where(PromptVersion.prompt_definition_id == d.id)):
        v.is_active = False
    db_session.commit()

    out = sync_platform_prompt_catalog(db_session)
    assert out.get("active_versions_repaired", 0) >= 1
    active = db_session.scalars(
        select(PromptVersion).where(PromptVersion.prompt_definition_id == d.id, PromptVersion.is_active.is_(True))
    ).first()
    assert active is not None
