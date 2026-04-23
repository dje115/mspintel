from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps.access import BearerIdentity, get_platform_admin
from app.api.deps.db import get_db
from app.api.deps.platform_mfa_actor import get_platform_mfa_actor
from app.core.request_meta import client_ip
from app.core.settings import get_settings
from app.models.entities import User
from app.schemas.platform import PlatformOverviewResponse, PlatformTenantListResponse
from app.schemas.platform_mfa import (
    PlatformMfaStatusResponse,
    TotpDisableRequest,
    TotpEnrollmentConfirmRequest,
    TotpEnrollmentStartResponse,
)
from app.schemas.system import SystemStatusResponse
from app.services.platform import PlatformService
from app.services.platform_mfa import PlatformMfaService

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


@router.get("/overview", response_model=PlatformOverviewResponse)
def platform_overview(
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> PlatformOverviewResponse:
    return PlatformService(db).overview()


@router.get("/tenants", response_model=PlatformTenantListResponse)
def platform_tenants(
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PlatformTenantListResponse:
    return PlatformService(db).tenants(page=page, page_size=page_size)


@router.get("/system-status", response_model=SystemStatusResponse)
def platform_system_status(
    _: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> SystemStatusResponse:
    return PlatformService(db).system_status()


@router.get("/mfa/status", response_model=PlatformMfaStatusResponse)
def platform_mfa_status(
    ctx: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> PlatformMfaStatusResponse:
    settings = get_settings()
    svc = PlatformMfaService(db)
    enabled, pending, mid = svc.get_totp_status(ctx.user.id)
    return PlatformMfaStatusResponse(
        totp_enabled=enabled,
        totp_pending=pending,
        platform_mfa_required=settings.platform_mfa_required,
        pending_method_id=mid if pending else None,
    )


@router.post("/mfa/totp/enrollment", response_model=TotpEnrollmentStartResponse)
def platform_totp_enrollment_start(
    request: Request,
    actor: User = Depends(get_platform_mfa_actor),
    db: Session = Depends(get_db),
) -> TotpEnrollmentStartResponse:
    ip = client_ip(request)
    svc = PlatformMfaService(db)
    try:
        method_id, uri = svc.start_totp_enrollment(actor, ip=ip)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return TotpEnrollmentStartResponse(method_id=method_id, otpauth_uri=uri)


@router.post("/mfa/totp/enrollment/confirm")
def platform_totp_enrollment_confirm(
    request: Request,
    payload: TotpEnrollmentConfirmRequest,
    actor: User = Depends(get_platform_mfa_actor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ip = client_ip(request)
    svc = PlatformMfaService(db)
    try:
        svc.confirm_totp_enrollment(actor, payload.method_id, payload.totp_code, ip=ip)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "ok"}


@router.post("/mfa/totp/disable")
def platform_totp_disable(
    request: Request,
    payload: TotpDisableRequest,
    ctx: BearerIdentity = Depends(get_platform_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Disable TOTP requires a full platform session (not only an enrolment setup token)."""
    ip = client_ip(request)
    svc = PlatformMfaService(db)
    try:
        svc.disable_totp(ctx.user, payload.totp_code, ip=ip)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "ok"}

