"""AIRuntimeResolver ensures tenant_ai_task_routes stubs exist (matches UI list_routes behaviour)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Tenant, TenantAiTaskRoute
from app.repositories.tenant_ai_config import TenantAiConfigRepository
from app.services.ai_runtime_resolver import AIRuntimeResolver


def test_resolver_inserts_stub_route_when_missing(db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ar1", name="AR1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    repo = TenantAiConfigRepository(db_session)
    assert repo.get_route_by_task(tenant.id, "customer_review_email_draft") is None
    AIRuntimeResolver(db_session).resolve(tenant.id, "customer_review_email_draft", include_prompt_text=False)
    row = repo.get_route_by_task(tenant.id, "customer_review_email_draft")
    assert row is not None
    assert row.enabled is True
    assert row.prompt_key == "customer_review_email_draft.system"


def test_resolver_stub_idempotent(db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ar2", name="AR2", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    r = AIRuntimeResolver(db_session)
    r.resolve(tenant.id, "customer_review_report", include_prompt_text=False)
    r.resolve(tenant.id, "customer_review_report", include_prompt_text=False)
    n = len(
        list(
            db_session.scalars(
                select(TenantAiTaskRoute).where(
                    TenantAiTaskRoute.tenant_id == tenant.id, TenantAiTaskRoute.task_type == "customer_review_report"
                )
            ).all()
        )
    )
    assert n == 1
