from uuid import UUID

from pydantic import BaseModel


class SourceConnectionResponse(BaseModel):
    id: UUID
    system_type: str
    display_name: str
    status: str
    last_sync_at: str | None
