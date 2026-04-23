from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.repositories.tenants import TenantRepository
from app.schemas.tenant import OnboardingStateResponse, OnboardingStateUpdate, SubscriptionSummary


class TenantService:
    def __init__(self, db: Session):
        self.repo = TenantRepository(db)

    def get_onboarding(self, tenant_id: UUID) -> OnboardingStateResponse:
        state = self.repo.onboarding(tenant_id)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding state not found")
        return OnboardingStateResponse(tenant_id=state.tenant_id, status=state.status, step=state.step)

    def update_onboarding(self, tenant_id: UUID, payload: OnboardingStateUpdate) -> OnboardingStateResponse:
        state = self.repo.onboarding(tenant_id)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding state not found")
        if payload.status is not None:
            state.status = payload.status
        if payload.step is not None:
            state.step = payload.step
        self.repo.db.commit()
        self.repo.db.refresh(state)
        return OnboardingStateResponse(tenant_id=state.tenant_id, status=state.status, step=state.step)

    def get_subscription(self, tenant_id: UUID) -> SubscriptionSummary:
        row = self.repo.subscription(tenant_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        subscription, plan = row
        return SubscriptionSummary(
            tenant_id=subscription.tenant_id,
            plan_code=plan.code,
            plan_name=plan.name,
            status=subscription.status,
        )
