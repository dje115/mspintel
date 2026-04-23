from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.deps.access import AccessContext, get_access_context, require_permission
from app.api.deps.db import get_db
from app.schemas.customer import CustomerDetailResponse, CustomerListResponse
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


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
def get_customer(
    customer_id: UUID,
    ctx: AccessContext = Depends(require_permission("customer:read")),
    db: Session = Depends(get_db),
):
    return CustomerService(db).get_customer_detail(ctx.tenant.id, customer_id)
