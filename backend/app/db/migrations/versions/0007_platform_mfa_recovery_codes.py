"""Platform MFA recovery codes (hashed, one-time).

Revision ID: 0007_platform_mfa_recovery_codes
Revises: 0006_user_mfa_methods
Create Date: 2026-04-23 22:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_platform_mfa_recovery_codes"
down_revision = "0006_user_mfa_methods"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_mfa_recovery_codes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_platform_mfa_recovery_user_unused",
        "platform_mfa_recovery_codes",
        ["user_id", "is_used"],
    )
    op.create_index(
        "ix_platform_mfa_recovery_user_batch",
        "platform_mfa_recovery_codes",
        ["user_id", "batch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_platform_mfa_recovery_user_batch", table_name="platform_mfa_recovery_codes")
    op.drop_index("ix_platform_mfa_recovery_user_unused", table_name="platform_mfa_recovery_codes")
    op.drop_table("platform_mfa_recovery_codes")
