from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models.entities import SourceSystemConnection, Tenant, User

settings = get_settings()


class SystemRepository:
    def __init__(self, db: Session):
        self.db = db

    def db_ok(self) -> bool:
        self.db.execute(text("SELECT 1"))
        return True

    def counts(self) -> tuple[int, int, int]:
        tenant_count = self.db.query(Tenant).count()
        user_count = self.db.query(User).count()
        source_connection_count = self.db.query(SourceSystemConnection).count()
        return tenant_count, user_count, source_connection_count

    def redis_status(self) -> str:
        # Runtime check kept lightweight for scaffold.
        return "configured" if settings.redis_url else "not_configured"
