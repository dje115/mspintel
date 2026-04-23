from pydantic import BaseModel


class Plan(BaseModel):
    id: int
    code: str
    name: str
    price_monthly_cents: int
    is_active: bool = True
