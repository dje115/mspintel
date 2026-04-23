from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.repositories.platform import PlatformRepository
from app.repositories.system import SystemRepository
from app.schemas.platform import (
    PlatformOverviewResponse,
    PlatformTenantListResponse,
    PlatformTenantRow,
)
from app.schemas.system import SystemStatusResponse
from app.services.system import SystemService


class PlatformService:
    def __init__(self, db: Session):
        self.db = db
        self.platform_repo = PlatformRepository(db)
        self.system_repo = SystemRepository(db)

    def overview(self) -> PlatformOverviewResponse:
        settings = get_settings()
        tenant_count, user_count, _ = self.system_repo.counts()
        sub_count = self.platform_repo.count_subscriptions()
        return PlatformOverviewResponse(
            tenant_count=tenant_count,
            user_count=user_count,
            subscription_count=sub_count,
            app_version=settings.app_version,
            environment=settings.environment,
        )

    def tenants(self, *, page: int, page_size: int) -> PlatformTenantListResponse:
        rows, total = self.platform_repo.list_tenants_page(page=page, page_size=page_size)
        items: list[PlatformTenantRow] = []
        for tenant, subscription, plan, onboarding in rows:
            items.append(
                PlatformTenantRow(
                    tenant_id=tenant.id,
                    name=tenant.name,
                    slug=tenant.slug,
                    is_active=tenant.is_active,
                    created_at=tenant.created_at,
                    onboarding_status=onboarding.status if onboarding else None,
                    onboarding_step=onboarding.step if onboarding else None,
                    subscription_status=subscription.status if subscription else None,
                    plan_code=plan.code if plan else None,
                    plan_name=plan.name if plan else None,
                )
            )
        return PlatformTenantListResponse(items=items, page=page, page_size=page_size, total=total)

    def system_status(self) -> SystemStatusResponse:
        return SystemService(self.db).status()
