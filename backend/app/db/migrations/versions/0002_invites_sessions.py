"""add tenant invitations and user sessions

Revision ID: 0002_invites_sessions
Revises: 0001_saas_core
Create Date: 2026-04-23 13:05:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_invites_sessions"
down_revision = "0001_saas_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role_to_assign", sa.String(length=50), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token", name="uq_tenant_invitations_token"),
    )
    op.create_index("ix_tenant_invitations_tenant", "tenant_invitations", ["tenant_id"])
    op.create_index("ix_tenant_invitations_email", "tenant_invitations", ["email"])
    op.create_index("ix_tenant_invitations_status", "tenant_invitations", ["status"])
    op.create_index("ix_tenant_invitations_expires", "tenant_invitations", ["expires_at"])

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=140), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("refresh_token_hash", name="uq_user_sessions_refresh_hash"),
    )
    op.create_index("ix_user_sessions_user", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires", "user_sessions", ["expires_at"])
    op.create_index("ix_user_sessions_revoked", "user_sessions", ["revoked_at"])


def downgrade() -> None:
    op.drop_table("user_sessions")
    op.drop_table("tenant_invitations")
