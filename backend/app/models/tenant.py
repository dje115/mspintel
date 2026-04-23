from pydantic import BaseModel


class Tenant(BaseModel):
    id: int
    slug: str
    name: str
    is_active: bool = True
