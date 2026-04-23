from pydantic import BaseModel


class Subscription(BaseModel):
    id: int
    tenant_id: int
    plan_id: int
    status: str
