from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.access import AccessContext, require_permission
from app.api.deps.db import get_db
from app.schemas.ai_execution import AIExecutionOutcome, AIProductBlockState
from app.schemas.customer import CustomerDetailResponse, CustomerListResponse
from app.services.ai_execution_service import AIExecutionService
from app.services.ai_product_context import (
    build_account_confidence_explanation_variables,
    build_account_manager_call_script_variables,
    build_account_manager_next_conversation_variables,
    build_account_summary_variables,
    build_billing_remediation_next_action_variables,
    build_billing_variance_summary_variables,
    build_churn_explanation_variables,
    build_customer_review_agenda_variables,
    build_m365_hygiene_summary_variables,
    build_m365_upsell_opportunity_variables,
    build_revenue_leakage_explanation_variables,
    build_risk_summary_variables,
    build_technical_gap_summary_variables,
    build_underbilling_opportunity_variables,
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


@router.get("/{customer_id}/ai/customer-review-agenda", response_model=AIProductBlockState)
def get_customer_review_agenda_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "customer_review_agenda", customer_id=customer_id)


@router.post("/{customer_id}/ai/customer-review-agenda", response_model=AIExecutionOutcome)
def post_customer_review_agenda_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_customer_review_agenda_variables(
        db,
        ctx.tenant.id,
        customer_id,
        caller_name=ctx.user.full_name,
        caller_email=ctx.user.email,
        caller_role=ctx.role_code,
    )
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="customer_review_agenda",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/account-manager-next-conversation", response_model=AIProductBlockState)
def get_account_manager_next_conversation_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(
        ctx.tenant.id, "account_manager_next_conversation", customer_id=customer_id
    )


@router.post("/{customer_id}/ai/account-manager-next-conversation", response_model=AIExecutionOutcome)
def post_account_manager_next_conversation_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_account_manager_next_conversation_variables(
        db,
        ctx.tenant.id,
        customer_id,
        caller_name=ctx.user.full_name,
        caller_email=ctx.user.email,
        caller_role=ctx.role_code,
    )
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="account_manager_next_conversation",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/account-manager-call-script", response_model=AIProductBlockState)
def get_account_manager_call_script_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(
        ctx.tenant.id, "account_manager_call_script", customer_id=customer_id
    )


@router.post("/{customer_id}/ai/account-manager-call-script", response_model=AIExecutionOutcome)
def post_account_manager_call_script_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_account_manager_call_script_variables(
        db,
        ctx.tenant.id,
        customer_id,
        caller_name=ctx.user.full_name,
        caller_email=ctx.user.email,
        caller_role=ctx.role_code,
    )
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="account_manager_call_script",
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


@router.get("/{customer_id}/ai/billing-variance-summary", response_model=AIProductBlockState)
def get_billing_variance_summary_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "billing_variance_summary", customer_id=customer_id)


@router.post("/{customer_id}/ai/billing-variance-summary", response_model=AIExecutionOutcome)
def post_billing_variance_summary_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_billing_variance_summary_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="billing_variance_summary",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/revenue-leakage-explanation", response_model=AIProductBlockState)
def get_revenue_leakage_explanation_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "revenue_leakage_explanation", customer_id=customer_id)


@router.post("/{customer_id}/ai/revenue-leakage-explanation", response_model=AIExecutionOutcome)
def post_revenue_leakage_explanation_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_revenue_leakage_explanation_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="revenue_leakage_explanation",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/billing-remediation-next-action", response_model=AIProductBlockState)
def get_billing_remediation_next_action_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "billing_remediation_next_action", customer_id=customer_id)


@router.post("/{customer_id}/ai/billing-remediation-next-action", response_model=AIExecutionOutcome)
def post_billing_remediation_next_action_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_billing_remediation_next_action_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="billing_remediation_next_action",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/underbilling-opportunity", response_model=AIProductBlockState)
def get_underbilling_opportunity_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "underbilling_opportunity", customer_id=customer_id)


@router.post("/{customer_id}/ai/underbilling-opportunity", response_model=AIExecutionOutcome)
def post_underbilling_opportunity_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_underbilling_opportunity_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="underbilling_opportunity",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/account-confidence-explanation", response_model=AIProductBlockState)
def get_account_confidence_explanation_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "account_confidence_explanation", customer_id=customer_id)


@router.post("/{customer_id}/ai/account-confidence-explanation", response_model=AIExecutionOutcome)
def post_account_confidence_explanation_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_account_confidence_explanation_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="account_confidence_explanation",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/m365-hygiene-summary", response_model=AIProductBlockState)
def get_m365_hygiene_summary_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "m365_hygiene_summary", customer_id=customer_id)


@router.post("/{customer_id}/ai/m365-hygiene-summary", response_model=AIExecutionOutcome)
def post_m365_hygiene_summary_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_m365_hygiene_summary_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="m365_hygiene_summary",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/m365-upsell-opportunity", response_model=AIProductBlockState)
def get_m365_upsell_opportunity_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "m365_upsell_opportunity", customer_id=customer_id)


@router.post("/{customer_id}/ai/m365-upsell-opportunity", response_model=AIExecutionOutcome)
def post_m365_upsell_opportunity_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_m365_upsell_opportunity_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="m365_upsell_opportunity",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )


@router.get("/{customer_id}/ai/technical-gap-summary", response_model=AIProductBlockState)
def get_technical_gap_summary_ai_state(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return AIExecutionService(db).read_block_state(ctx.tenant.id, "technical_gap_summary", customer_id=customer_id)


@router.post("/{customer_id}/ai/technical-gap-summary", response_model=AIExecutionOutcome)
def post_technical_gap_summary_ai(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    variables = build_technical_gap_summary_variables(db, ctx.tenant.id, customer_id)
    return AIExecutionService(db).execute(
        tenant_id=ctx.tenant.id,
        task_type="technical_gap_summary",
        variables=variables,
        actor_user_id=ctx.user.id,
        customer_id=customer_id,
    )
