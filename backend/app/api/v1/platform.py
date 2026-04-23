from fastapi import APIRouter, Depends

from app.api.deps.access import AccessContext, get_access_context

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


@router.get("/context")
def platform_context(access: AccessContext = Depends(get_access_context)) -> dict[str, str | None]:
    return {
        "user_id": access.user_id,
        "tenant_slug": access.tenant_slug,
        "platform_role": access.platform_role,
        "mode": "saas-scaffold",
    }
