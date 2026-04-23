"""add session metadata columns

Revision ID: 0004_session_metadata
Revises: 0003_security_hardening
Create Date: 2026-04-23 15:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_session_metadata"
down_revision = "0003_security_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_sessions", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.add_column("user_sessions", sa.Column("user_agent", sa.Text(), nullable=True))
    op.add_column("user_sessions", sa.Column("device_label", sa.String(length=200), nullable=True))
    op.add_column(
        "user_sessions",
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_sessions", "last_used_at")
    op.drop_column("user_sessions", "device_label")
    op.drop_column("user_sessions", "user_agent")
    op.drop_column("user_sessions", "ip_address")
