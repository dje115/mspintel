from pydantic import BaseModel


class User(BaseModel):
    id: int
    email: str
    display_name: str | None = None
    is_platform_admin: bool = False
