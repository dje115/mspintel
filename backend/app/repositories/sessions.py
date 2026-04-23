from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import UserSession


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, session: UserSession) -> UserSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def by_refresh_hash(self, token_hash: str) -> UserSession | None:
        return self.db.scalars(
            select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        ).first()

    def revoke(self, session: UserSession) -> None:
        session.revoked_at = datetime.now(UTC)
        self.db.commit()

    def revoke_all_for_user(self, user_id: UUID) -> int:
        rows = self.db.scalars(select(UserSession).where(UserSession.user_id == user_id)).all()
        now = datetime.now(UTC)
        for row in rows:
            row.revoked_at = now
        self.db.commit()
        return len(rows)

    def is_active(self, session: UserSession) -> bool:
        if session.revoked_at is not None:
            return False
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires > datetime.now(UTC)
