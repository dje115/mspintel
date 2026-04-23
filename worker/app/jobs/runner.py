"""Periodic jobs. See repository/docs: ``docs/WORKER.md``."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, text

from app.core.settings import get_settings


def run_invitation_sweep() -> int:
    """Expire overdue pending invitations (Postgres). Mirrors ``InvitationRepository.expire_pending_past_expiry``."""
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    stmt = text(
        """
        UPDATE tenant_invitations
        SET status = 'expired', updated_at = NOW()
        WHERE status = 'pending' AND expires_at < NOW()
        """
    )
    with engine.begin() as conn:
        res = conn.execute(stmt)
        return int(res.rowcount or 0)


def run_placeholder_jobs() -> None:
    settings = get_settings()
    n = run_invitation_sweep()
    print(f"[{datetime.now(UTC).isoformat()}] invitation_sweep expired_rows={n}")
    print(
        f"[{datetime.now(UTC).isoformat()}] {settings.project_name} worker poll "
        f"(billing_provider={settings.billing_provider}, redis={settings.redis_url})"
    )
