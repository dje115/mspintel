"""Platform-operator MFA methods (TOTP first; WebAuthn-ready schema).

Stores encrypted TOTP material in ``ciphertext``; ``method_metadata`` reserved for future
WebAuthn credentials. One row per (``user_id``, ``method_type``).

Revision ID: 0006_user_mfa_methods
Revises: 0005_platform_session_audit
Create Date: 2026-04-23 19:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_user_mfa_methods"
down_revision = "0005_platform_session_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_mfa_methods",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method_type", sa.String(length=32), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("method_label", sa.String(length=120), nullable=False, server_default="Authenticator app"),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("method_metadata", sa.JSON(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "method_type", name="uq_user_mfa_method_type"),
    )
    op.create_index("ix_user_mfa_methods_user_id", "user_mfa_methods", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_mfa_methods_user_id", table_name="user_mfa_methods")
    op.drop_table("user_mfa_methods")
