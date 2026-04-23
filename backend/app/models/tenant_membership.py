from pydantic import BaseModel


class TenantMembership(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    role: str
    status: str
