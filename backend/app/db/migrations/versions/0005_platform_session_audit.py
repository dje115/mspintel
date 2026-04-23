"""platform session auth_mode and nullable audit tenant

Revision ID: 0005_platform_session_audit
Revises: 0004_session_metadata
Create Date: 2026-04-23 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_platform_session_audit"
down_revision = "0004_session_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_sessions",
        sa.Column("auth_mode", sa.String(length=16), nullable=False, server_default="tenant"),
    )
    op.create_index("ix_user_sessions_user_auth", "user_sessions", ["user_id", "auth_mode"])
    op.alter_column("audit_events", "tenant_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.alter_column("audit_events", "tenant_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_index("ix_user_sessions_user_auth", table_name="user_sessions")
    op.drop_column("user_sessions", "auth_mode")
