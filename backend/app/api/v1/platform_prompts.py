from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.access import BearerIdentity, get_platform_admin
from app.api.deps.db import get_db
from app.schemas.ai_foundation import (
    PlatformPromptDefinitionCreate,
    PromptDetailResponse,
    PromptVersionCreateBody,
)
from app.services.prompt_application import PromptApplicationService

router = APIRouter(prefix="/api/v1/platform/prompts", tags=["platform-prompts"])


@router.get("", response_model=list[PromptDetailResponse])
def platform_list_prompts(
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).platform_list_prompts()


@router.post("", response_model=PromptDetailResponse)
def platform_create_prompt(
    body: PlatformPromptDefinitionCreate,
    ctx: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).platform_create_definition(ctx.user.id, body)


@router.post("/{definition_id}/versions", response_model=PromptDetailResponse)
def platform_add_prompt_version(
    definition_id: UUID,
    body: PromptVersionCreateBody,
    ctx: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).platform_add_version(ctx.user.id, definition_id, body)


@router.post("/{definition_id}/activate/{version_id}", response_model=PromptDetailResponse)
def platform_activate_prompt_version(
    definition_id: UUID,
    version_id: UUID,
    ctx: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    return PromptApplicationService(db).platform_activate(ctx.user.id, definition_id, version_id)
