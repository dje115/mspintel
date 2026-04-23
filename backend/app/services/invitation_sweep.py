"""Background job: mark overdue pending invitations as expired (idempotent)."""

from sqlalchemy.orm import Session

from app.repositories.invitations import InvitationRepository


def sweep_expired_invitations(db: Session) -> int:
    return InvitationRepository(db).expire_pending_past_expiry()
