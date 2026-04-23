from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.token_policy import normalized_session_auth_mode
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

    def get_for_user(self, session_id: UUID, user_id: UUID) -> UserSession | None:
        return self.db.scalars(
            select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user_id)
        ).first()

    def list_for_user_in_auth_mode(self, user_id: UUID, auth_mode: str) -> list[UserSession]:
        am = normalized_session_auth_mode(auth_mode)
        return list(
            self.db.scalars(
                select(UserSession)
                .where(UserSession.user_id == user_id, UserSession.auth_mode == am)
                .order_by(UserSession.created_at.desc())
            ).all()
        )

    def revoke(self, session: UserSession) -> None:
        session.revoked_at = datetime.now(UTC)
        self.db.commit()

    def touch(self, session: UserSession) -> None:
        session.last_used_at = datetime.now(UTC)
        self.db.commit()

    def revoke_all_for_user_in_auth_mode(self, user_id: UUID, auth_mode: str) -> int:
        am = normalized_session_auth_mode(auth_mode)
        rows = self.db.scalars(
            select(UserSession).where(UserSession.user_id == user_id, UserSession.auth_mode == am)
        ).all()
        now = datetime.now(UTC)
        for row in rows:
            row.revoked_at = now
        self.db.commit()
        return len(rows)

    def revoke_all_for_user_except_refresh_hash_in_auth_mode(
        self, user_id: UUID, keep_hash: str, auth_mode: str
    ) -> int:
        am = normalized_session_auth_mode(auth_mode)
        rows = self.db.scalars(
            select(UserSession).where(UserSession.user_id == user_id, UserSession.auth_mode == am)
        ).all()
        now = datetime.now(UTC)
        n = 0
        for row in rows:
            if row.refresh_token_hash == keep_hash:
                continue
            if row.revoked_at is None:
                row.revoked_at = now
                n += 1
        self.db.commit()
        return n

    def is_active(self, session: UserSession) -> bool:
        if session.revoked_at is not None:
            return False
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires > datetime.now(UTC)
