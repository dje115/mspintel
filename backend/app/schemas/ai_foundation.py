"""Schemas for tenant AI settings, task routes, catalog, and prompts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AIProviderCatalogCreate(BaseModel):
    code: str
    provider_family: str
    deployment_mode: str
    display_name: str
    description: str | None = None
    sort_order: int = 0


class AIProviderCatalogRow(BaseModel):
    id: UUID
    code: str
    provider_family: str
    deployment_mode: str
    display_name: str
    description: str | None = None
    sort_order: int


class AIProviderSafe(BaseModel):
    id: UUID
    tenant_id: UUID | None
    provider_name: str
    status: str
    catalog_code: str | None
    provider_family: str | None
    deployment_mode: str | None
    display_label: str | None
    base_url: str | None
    has_encrypted_settings: bool = False
    is_enabled: bool


class AIProviderCreateBody(BaseModel):
    catalog_code: str | None = None
    provider_family: str
    deployment_mode: str
    display_label: str | None = None
    base_url: str | None = None
    settings: dict | None = Field(default=None, description="Non-secret config; secrets stored encrypted server-side")


class TenantAiSettingsResponse(BaseModel):
    tenant_id: UUID
    default_ai_provider: AIProviderSafe | None
    default_model: str | None
    fallback_ai_provider: AIProviderSafe | None
    fallback_model: str | None
    extra: dict | None = None


class TenantAiSettingsPatch(BaseModel):
    default_ai_provider_id: UUID | None = None
    default_model: str | None = None
    fallback_ai_provider_id: UUID | None = None
    fallback_model: str | None = None
    extra: dict | None = None


class TenantAiTaskRouteRow(BaseModel):
    id: UUID
    task_type: str
    ai_provider: AIProviderSafe | None
    model: str | None
    fallback_ai_provider: AIProviderSafe | None
    fallback_model: str | None
    prompt_key: str
    enabled: bool


class TenantAiTaskRoutePatchItem(BaseModel):
    task_type: str
    ai_provider_id: UUID | None = None
    model: str | None = None
    fallback_ai_provider_id: UUID | None = None
    fallback_model: str | None = None
    prompt_key: str
    enabled: bool = True


class TenantAiTaskRoutesPatch(BaseModel):
    routes: list[TenantAiTaskRoutePatchItem]


class PromptVersionRow(BaseModel):
    id: UUID
    version_number: int
    change_note: str | None
    is_active: bool
    created_at: datetime
    created_by_user_id: UUID | None = None
    version_metadata: dict | None = None


class PromptListItem(BaseModel):
    prompt_key: str
    task_type: str
    title: str
    source: str = Field(description="platform | tenant_override")
    definition_id: UUID
    active_version_id: UUID | None
    active_version_number: int | None


class PromptDetailResponse(BaseModel):
    definition_id: UUID
    prompt_key: str
    task_type: str
    title: str
    description: str | None
    scope: str
    tenant_id: UUID | None
    active_version: PromptVersionRow | None
    versions: list[PromptVersionRow]


class PromptVersionCreateBody(BaseModel):
    prompt_text: str
    change_note: str | None = None
    version_metadata: dict | None = None


class RevertPromptBody(BaseModel):
    prompt_key: str


class TenantPromptOverrideCreate(BaseModel):
    prompt_key: str
    title: str
    task_type: str
    initial_version: PromptVersionCreateBody


class PlatformPromptDefinitionCreate(BaseModel):
    prompt_key: str
    title: str
    task_type: str
    description: str | None = None
    initial_version: PromptVersionCreateBody


class PromptCompareResponse(BaseModel):
    left: PromptVersionRow
    right: PromptVersionRow
    left_preview: str
    right_preview: str


class ResolvedAITaskResponse(BaseModel):
    tenant_id: UUID
    task_type: str
    enabled: bool
    provider_family: str | None
    deployment_mode: str | None
    model: str | None
    ai_provider_id: UUID | None
    prompt_key: str
    prompt_definition_id: UUID | None
    prompt_version_id: UUID | None
    prompt_text: str | None = Field(default=None, description="Resolved active prompt body when requested")
    fallback_ai_provider_id: UUID | None = None
    fallback_provider_family: str | None = None
    fallback_deployment_mode: str | None = None
    fallback_model: str | None = None
