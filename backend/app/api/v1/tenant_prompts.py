from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.ai_foundation import (
    PromptCompareResponse,
    PromptDetailResponse,
    PromptListItem,
    PromptVersionCreateBody,
    PromptVersionRow,
    RevertPromptBody,
    TenantPromptOverrideCreate,
)
from app.services.prompt_application import PromptApplicationService

router = APIRouter(prefix="/api/v1/prompts", tags=["tenant-prompts"])


@router.get("", response_model=list[PromptListItem])
def list_prompts(
    ctx: AccessContext = Depends(require_permission("ai:view")),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).list_prompts_for_tenant(ctx.tenant.id)


@router.post("/revert-to-default")
def revert_prompt_to_default(
    body: RevertPromptBody,
    ctx: AccessContext = Depends(require_permission("ai:configure")),
    db: Session = Depends(get_db),
):
    PromptApplicationService(db).revert_to_platform_default(ctx.tenant.id, ctx.user.id, body.prompt_key)
    return {"status": "ok", "prompt_key": body.prompt_key}


@router.post("/tenant-overrides", response_model=PromptDetailResponse)
def create_tenant_override(
    body: TenantPromptOverrideCreate,
    ctx: AccessContext = Depends(require_permission("ai:configure")),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).create_tenant_override(
        ctx.tenant.id,
        ctx.user.id,
        body.prompt_key,
        body.initial_version,
        title=body.title,
        task_type=body.task_type,
    )


@router.get("/{definition_id}/compare", response_model=PromptCompareResponse)
def compare_versions(
    definition_id: UUID,
    left_id: UUID,
    right_id: UUID,
    ctx: AccessContext = Depends(require_permission("ai:view")),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).compare_versions(ctx.tenant.id, definition_id, left_id, right_id)


@router.get("/{definition_id}/versions", response_model=list[PromptVersionRow])
def list_versions(
    definition_id: UUID,
    ctx: AccessContext = Depends(require_permission("ai:view")),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).list_versions_for_tenant(ctx.tenant.id, definition_id)


@router.get("/{definition_id}", response_model=PromptDetailResponse)
def get_prompt(
    definition_id: UUID,
    ctx: AccessContext = Depends(require_permission("ai:view")),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).get_prompt_detail(ctx.tenant.id, definition_id)


@router.post("/{definition_id}/versions", response_model=PromptDetailResponse)
def add_prompt_version(
    definition_id: UUID,
    body: PromptVersionCreateBody,
    ctx: AccessContext = Depends(require_permission("ai:configure")),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).add_version(ctx.tenant.id, ctx.user.id, definition_id, body)


@router.post("/{definition_id}/activate/{version_id}", response_model=PromptDetailResponse)
def activate_prompt_version(
    definition_id: UUID,
    version_id: UUID,
    ctx: AccessContext = Depends(require_permission("ai:configure")),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).activate_version(ctx.tenant.id, ctx.user.id, definition_id, version_id)
