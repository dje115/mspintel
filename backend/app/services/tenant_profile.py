from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import TenantMspProfile, TenantServiceCatalogEntry
from app.schemas.tenant_profile import (
    DEFAULT_SERVICE_CATALOG,
    TenantAIContextResponse,
    TenantMspProfilePayload,
    TenantMspProfileResponse,
    TenantServiceCatalogEntryPayload,
    TenantServiceCatalogResponse,
)
from app.services.audit import AuditService


class TenantProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    def _profile(self, tenant_id: UUID) -> TenantMspProfile | None:
        return self.db.scalars(select(TenantMspProfile).where(TenantMspProfile.tenant_id == tenant_id)).first()

    def get_profile(self, tenant_id: UUID) -> TenantMspProfileResponse:
        p = self._profile(tenant_id)
        if not p:
            return TenantMspProfileResponse(tenant_id=tenant_id)
        return TenantMspProfileResponse(
            tenant_id=tenant_id,
            legal_name=p.legal_name,
            brand_name=p.brand_name,
            regions_served=list(p.regions_served or []),
            vertical_focus=list(p.vertical_focus or []),
            team_size_band=p.team_size_band,
            customer_count_band=p.customer_count_band,
            typical_customer_size_band=p.typical_customer_size_band,
            delivery_model=p.delivery_model,
            business_goals=list(p.business_goals or []),
            free_text_description=p.free_text_description,
        )

    def put_profile(self, tenant_id: UUID, actor_user_id: UUID, payload: TenantMspProfilePayload) -> TenantMspProfileResponse:
        p = self._profile(tenant_id)
        if not p:
            p = TenantMspProfile(tenant_id=tenant_id)
            self.db.add(p)
        p.legal_name = payload.legal_name
        p.brand_name = payload.brand_name
        p.regions_served = payload.regions_served
        p.vertical_focus = payload.vertical_focus
        p.team_size_band = payload.team_size_band
        p.customer_count_band = payload.customer_count_band
        p.typical_customer_size_band = payload.typical_customer_size_band
        p.delivery_model = payload.delivery_model
        p.business_goals = payload.business_goals
        p.free_text_description = payload.free_text_description
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type="tenant.profile.updated",
            details={
                "team_size_band": payload.team_size_band,
                "customer_count_band": payload.customer_count_band,
                "service_model": payload.delivery_model,
            },
        )
        self.db.commit()
        return self.get_profile(tenant_id)

    def _catalog_rows(self, tenant_id: UUID) -> list[TenantServiceCatalogEntry]:
        return list(
            self.db.scalars(
                select(TenantServiceCatalogEntry)
                .where(TenantServiceCatalogEntry.tenant_id == tenant_id)
                .order_by(TenantServiceCatalogEntry.sort_order.asc(), TenantServiceCatalogEntry.service_name.asc())
            ).all()
        )

    def get_service_catalog(self, tenant_id: UUID) -> TenantServiceCatalogResponse:
        rows = self._catalog_rows(tenant_id)
        if not rows:
            return TenantServiceCatalogResponse(
                tenant_id=tenant_id,
                items=[
                    TenantServiceCatalogEntryPayload(
                        service_key=key, service_name=label, is_selected=False, is_custom=False, sort_order=i
                    )
                    for i, (key, label) in enumerate(DEFAULT_SERVICE_CATALOG)
                ],
            )
        return TenantServiceCatalogResponse(
            tenant_id=tenant_id,
            items=[
                TenantServiceCatalogEntryPayload(
                    service_key=r.service_key,
                    service_name=r.service_name,
                    is_selected=r.is_selected,
                    is_custom=r.is_custom,
                    sort_order=r.sort_order,
                )
                for r in rows
            ],
        )

    def put_service_catalog(
        self, tenant_id: UUID, actor_user_id: UUID, payload: TenantServiceCatalogResponse
    ) -> TenantServiceCatalogResponse:
        if payload.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant mismatch")
        self.db.execute(delete(TenantServiceCatalogEntry).where(TenantServiceCatalogEntry.tenant_id == tenant_id))
        for i, item in enumerate(payload.items):
            self.db.add(
                TenantServiceCatalogEntry(
                    tenant_id=tenant_id,
                    service_key=item.service_key.strip().lower().replace(" ", "_"),
                    service_name=item.service_name.strip(),
                    is_selected=bool(item.is_selected),
                    is_custom=bool(item.is_custom),
                    sort_order=int(item.sort_order if item.sort_order is not None else i),
                )
            )
        self.audit.log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type="tenant.service_catalog.updated",
            details={"item_count": len(payload.items), "selected_count": sum(1 for i in payload.items if i.is_selected)},
        )
        self.db.commit()
        return self.get_service_catalog(tenant_id)


def build_tenant_ai_context(db: Session, tenant_id: UUID) -> TenantAIContextResponse:
    svc = TenantProfileService(db)
    profile = svc.get_profile(tenant_id)
    catalog = svc.get_service_catalog(tenant_id)
    selected_services = [i.service_name for i in catalog.items if i.is_selected]
    notes: list[str] = []
    if not profile.legal_name and not profile.brand_name:
        notes.append("MSP legal/brand profile is incomplete.")
    if not selected_services:
        notes.append("No service catalogue items selected yet.")
    if not profile.business_goals:
        notes.append("Business goals are not configured; AI should keep recommendations generic.")
    return TenantAIContextResponse(
        tenant_id=tenant_id,
        msp_profile_summary={
            "legal_name": profile.legal_name,
            "brand_name": profile.brand_name,
            "delivery_model": profile.delivery_model,
            "team_size_band": profile.team_size_band,
            "customer_count_band": profile.customer_count_band,
            "typical_customer_size_band": profile.typical_customer_size_band,
            "free_text_description": profile.free_text_description,
        },
        selected_services=selected_services,
        business_goals=profile.business_goals,
        vertical_focus=profile.vertical_focus,
        regions_served=profile.regions_served,
        data_confidence_notes=notes or ["Tenant MSP profile context is available."],
    )

