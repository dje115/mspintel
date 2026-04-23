from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.repositories.system import SystemRepository
from app.schemas.system import SystemStatusResponse

settings = get_settings()


class SystemService:
    def __init__(self, db: Session):
        self.repo = SystemRepository(db)

    def status(self) -> SystemStatusResponse:
        db_state = "ok"
        try:
            self.repo.db_ok()
        except Exception:
            db_state = "error"

        tenant_count, user_count, source_connection_count = self.repo.counts()
        return SystemStatusResponse(
            api="ok",
            environment=settings.environment,
            version=settings.app_version,
            db=db_state,
            redis=self.repo.redis_status(),
            tenant_count=tenant_count,
            user_count=user_count,
            source_connection_count=source_connection_count,
        )
