from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.ai_execution import AIExecutionOutcome, AIProductBlockState
from app.schemas.customer import CustomerDetailResponse, CustomerListResponse
from app.services.ai_execution_service import AIExecutionService
from app.services.ai_product_context import (
    build_account_summary_variables,
    build_churn_explanation_variables,
    build_risk_summary_variables,
)
from app.services.customer import CustomerService

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("", response_model=CustomerListResponse)
def list_customers(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return CustomerService(db).list_customers(ctx.tenant.id, search, status, page, page_size)


@router.get("/{customer_id}/ai/account-summary", response_model=AIProductBlockState)
def get_account_summary_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "account_summary", customer_id=customer_id)


@router.post("/{customer_id}/ai/account-summary", response_model=AIExecutionOutcome)
def post_account_summary_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_account_summary_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="account_summary",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/risk-summary", response_model=AIProductBlockState)
def get_risk_summary_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "risk_summary", customer_id=customer_id)


@router.post("/{customer_id}/ai/risk-summary", response_model=AIExecutionOutcome)
def post_risk_summary_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_risk_summary_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="risk_summary",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/churn-explanation", response_model=AIProductBlockState)
def get_churn_explanation_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "churn_explanation", customer_id=customer_id)


@router.post("/{customer_id}/ai/churn-explanation", response_model=AIExecutionOutcome)
def post_churn_explanation_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_churn_explanation_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="churn_explanation",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
def get_customer(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return CustomerService(db).get_customer_detail(ctx.tenant.id, customer_id)
