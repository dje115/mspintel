"""Tenant AI settings and task-route orchestration."""

from __future__ import annotations

import json
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.ai_settings_crypto import encrypt_settings_payload, redact_settings_for_api
from app.domain.ai_constants import AI_TASK_TYPES
from app.models.entities import AIProvider, TenantAiSettings, TenantAiTaskRoute
from app.repositories.tenant_ai_config import TenantAiConfigRepository
from app.schemas.ai_foundation import (
    AIProviderSafe,
    TenantAiSettingsPatch,
    TenantAiSettingsResponse,
    TenantAiTaskRouteRow,
    TenantAiTaskRoutesPatch,
)
from app.services.audit import AuditService


def provider_to_safe(p: AIProvider | None) -> AIProviderSafe | None:
    if not p:
        return None
    return AIProviderSafe(
        id=p.id,
        tenant_id=p.tenant_id,
        provider_name=p.provider_name,
        status=p.status,
        catalog_code=p.catalog_code,
        provider_family=p.provider_family,
        deployment_mode=p.deployment_mode,
        display_label=p.display_label,
        base_url=p.base_url,
        has_encrypted_settings=bool(p.encrypted_settings),
        is_enabled=p.is_enabled,
    )


class TenantAiApplicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TenantAiConfigRepository(db)
        self.audit = AuditService(db)

    def get_settings(self, tenant_id: UUID) -> TenantAiSettingsResponse:
        row = self.repo.get_settings(tenant_id)
        default_p = (
            self.db.get(AIProvider, row.default_ai_provider_id) if row and row.default_ai_provider_id else None
        )
        fb_p = (
            self.db.get(AIProvider, row.fallback_ai_provider_id) if row and row.fallback_ai_provider_id else None
        )
        if default_p and default_p.tenant_id != tenant_id:
            default_p = None
        if fb_p and fb_p.tenant_id != tenant_id:
            fb_p = None
        return TenantAiSettingsResponse(
            tenant_id=tenant_id,
            default_ai_provider=provider_to_safe(default_p),
            default_model=row.default_model if row else None,
            fallback_ai_provider=provider_to_safe(fb_p),
            fallback_model=row.fallback_model if row else None,
            extra=row.extra if row else None,
        )

    def patch_settings(
        self, tenant_id: UUID, actor_id: UUID, body: TenantAiSettingsPatch
    ) -> TenantAiSettingsResponse:
        patch = body.model_dump(exclude_unset=True)
        existing_row = self.repo.get_settings(tenant_id)
        fields = {
            "default_ai_provider_id": existing_row.default_ai_provider_id if existing_row else None,
            "default_model": existing_row.default_model if existing_row else None,
            "fallback_ai_provider_id": existing_row.fallback_ai_provider_id if existing_row else None,
            "fallback_model": existing_row.fallback_model if existing_row else None,
            "extra": existing_row.extra if existing_row else None,
        }
        fields.update(patch)

        if fields.get("default_ai_provider_id"):
            p = self.repo.get_ai_provider(tenant_id, fields["default_ai_provider_id"])
            if not p:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid default_ai_provider_id")
        if fields.get("fallback_ai_provider_id"):
            p = self.repo.get_ai_provider(tenant_id, fields["fallback_ai_provider_id"])
            if not p:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid fallback_ai_provider_id")
        row = TenantAiSettings(
            tenant_id=tenant_id,
            default_ai_provider_id=fields["default_ai_provider_id"],
            default_model=fields["default_model"],
            fallback_ai_provider_id=fields["fallback_ai_provider_id"],
            fallback_model=fields["fallback_model"],
            extra=fields["extra"],
            updated_by_user_id=actor_id,
        )
        self.repo.upsert_settings(row)
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            event_type="ai.tenant_settings.updated",
            details={"patch": json.loads(body.model_dump_json(exclude_unset=True))},
        )
        self.db.commit()
        return self.get_settings(tenant_id)

    def list_routes(self, tenant_id: UUID) -> list[TenantAiTaskRouteRow]:
        existing = {r.task_type: r for r in self.repo.list_task_routes(tenant_id)}
        out: list[TenantAiTaskRouteRow] = []
        for tt in AI_TASK_TYPES:
            r = existing.get(tt)
            if r:
                ap = self.db.get(AIProvider, r.ai_provider_id) if r.ai_provider_id else None
                fb = self.db.get(AIProvider, r.fallback_ai_provider_id) if r.fallback_ai_provider_id else None
                if ap and ap.tenant_id != tenant_id:
                    ap = None
                if fb and fb.tenant_id != tenant_id:
                    fb = None
                out.append(
                    TenantAiTaskRouteRow(
                        id=r.id,
                        task_type=r.task_type,
                        ai_provider=provider_to_safe(ap),
                        model=r.model,
                        fallback_ai_provider=provider_to_safe(fb),
                        fallback_model=r.fallback_model,
                        prompt_key=r.prompt_key,
                        enabled=r.enabled,
                    )
                )
            else:
                pk = f"{tt}.system"
                stub = TenantAiTaskRoute(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    task_type=tt,
                    ai_provider_id=None,
                    model=None,
                    fallback_ai_provider_id=None,
                    fallback_model=None,
                    prompt_key=pk,
                    enabled=True,
                )
                self.repo.upsert_route(stub)
                self.db.commit()
                out.append(
                    TenantAiTaskRouteRow(
                        id=stub.id,
                        task_type=stub.task_type,
                        ai_provider=None,
                        model=None,
                        fallback_ai_provider=None,
                        fallback_model=None,
                        prompt_key=stub.prompt_key,
                        enabled=stub.enabled,
                    )
                )
        return out

    def patch_routes(self, tenant_id: UUID, actor_id: UUID, body: TenantAiTaskRoutesPatch) -> list[TenantAiTaskRouteRow]:
        for item in body.routes:
            if item.task_type not in AI_TASK_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown task_type {item.task_type}"
                )
            if item.ai_provider_id:
                p = self.repo.get_ai_provider(tenant_id, item.ai_provider_id)
                if not p:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ai_provider_id")
            if item.fallback_ai_provider_id:
                p = self.repo.get_ai_provider(tenant_id, item.fallback_ai_provider_id)
                if not p:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid fallback_ai_provider_id"
                    )
            row = TenantAiTaskRoute(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                task_type=item.task_type,
                ai_provider_id=item.ai_provider_id,
                model=item.model,
                fallback_ai_provider_id=item.fallback_ai_provider_id,
                fallback_model=item.fallback_model,
                prompt_key=item.prompt_key,
                enabled=item.enabled,
            )
            self.repo.upsert_route(row)
            self.audit.log(
                tenant_id=tenant_id,
                actor_user_id=actor_id,
                event_type="ai.task_route.updated",
                details={"task_type": item.task_type, "prompt_key": item.prompt_key, "enabled": item.enabled},
            )
        self.db.commit()
        return self.list_routes(tenant_id)

    def create_tenant_provider(
        self,
        tenant_id: UUID,
        actor_user_id: UUID,
        *,
        catalog_code: str | None,
        provider_family: str,
        deployment_mode: str,
        display_label: str | None,
        base_url: str | None,
        settings: dict | None,
        provider_name: str,
    ) -> AIProviderSafe:
        enc = encrypt_settings_payload(settings or {}) if settings else None
        row = AIProvider(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider_name=provider_name,
            status="configured",
            catalog_code=catalog_code,
            provider_family=provider_family,
            deployment_mode=deployment_mode,
            display_label=display_label,
            base_url=base_url,
            encrypted_settings=enc,
            is_enabled=True,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type="ai.provider.created",
            details={
                "provider_id": str(row.id),
                "provider_family": provider_family,
                "deployment_mode": deployment_mode,
                "settings": redact_settings_for_api(settings or {}) or {},
            },
        )
        self.db.commit()
        return provider_to_safe(row)  # type: ignore[return-value]
