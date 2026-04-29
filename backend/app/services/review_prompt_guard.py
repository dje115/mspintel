"""Pre-flight checks for Review/QBR AI tasks (prompt availability)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.ai_runtime_resolver import AIRuntimeResolver

SYNC_REMEDIATION = (
    "Run `docker compose exec backend python -m app.scripts.sync_platform_prompt_defaults` "
    "(or from backend dir: `python -m app.scripts.sync_platform_prompt_defaults` with DATABASE_URL set). "
    "Platform operators can also add prompts under /platform/prompts."
)


def assert_review_ai_task_prompt_available(db: Session, tenant_id: UUID, task_type: str) -> None:
    """Raise HTTP 503 with actionable detail when no active prompt text can be resolved for this task."""
    resolved = AIRuntimeResolver(db).resolve(tenant_id, task_type, include_prompt_text=True)
    if resolved.prompt_text and resolved.prompt_definition_id:
        return
    msg = (
        f"No active prompt is available for AI task {task_type!r} (prompt_key={resolved.prompt_key!r}). "
        f"{SYNC_REMEDIATION}"
    )
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=msg)
