from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customer_router
from app.api.v1.dashboards import router as dashboard_router
from app.api.v1.health import router as health_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.platform import router as platform_router
from app.api.v1.platform_ai import router as platform_ai_router
from app.api.v1.platform_prompts import router as platform_prompts_router
from app.api.v1.system import router as system_router
from app.api.v1.tenants import root_router as invitations_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.tenant_profile import router as tenant_profile_router
from app.api.v1.tenant_ai import router as tenant_ai_router
from app.api.v1.tenant_prompts import router as tenant_prompts_router
from app.api.v1.workspace import router as workspace_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(platform_router)
api_router.include_router(platform_ai_router)
api_router.include_router(platform_prompts_router)
api_router.include_router(tenants_router)
api_router.include_router(tenant_profile_router)
api_router.include_router(invitations_router)
api_router.include_router(integrations_router)
api_router.include_router(customer_router)
api_router.include_router(dashboard_router)
api_router.include_router(system_router)
api_router.include_router(workspace_router)
api_router.include_router(tenant_ai_router)
api_router.include_router(tenant_prompts_router)
