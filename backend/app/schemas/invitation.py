from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role_to_assign: str


class InvitationResponse(BaseModel):
    id: UUID
    email: EmailStr
    role_to_assign: str
    status: str
    accept_url: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    debug_token: str | None = None


class InvitationAcceptRequest(BaseModel):
    token: str
    full_name: str | None = None
    password: str | None = None


class InvitationAcceptResponse(BaseModel):
    status: str
    tenant_id: UUID
    user_id: UUID
