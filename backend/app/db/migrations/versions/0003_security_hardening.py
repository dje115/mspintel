"""invitation and session hardening constraints

Revision ID: 0003_security_hardening
Revises: 0002_invites_sessions
Create Date: 2026-04-23 14:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_security_hardening"
down_revision = "0002_invites_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_tenant_invitations_status_valid",
        "tenant_invitations",
        "status IN ('pending', 'accepted', 'expired', 'revoked')",
    )
    op.create_check_constraint(
        "ck_user_sessions_expiry_order",
        "user_sessions",
        "expires_at > created_at",
    )
    op.create_index(
        "ix_tenant_invitations_pending_unique",
        "tenant_invitations",
        ["tenant_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_invitations_pending_unique", table_name="tenant_invitations")
    op.drop_constraint("ck_user_sessions_expiry_order", "user_sessions", type_="check")
    op.drop_constraint("ck_tenant_invitations_status_valid", "tenant_invitations", type_="check")
