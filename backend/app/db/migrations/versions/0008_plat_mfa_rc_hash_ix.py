"""Index platform recovery lookup by user + code hash.

Revision ID: 0008_plat_mfa_rc_hash_ix (<=32 chars for ``alembic_version``).
Revises: 0007_platform_mfa_recovery_codes
Create Date: 2026-04-23
"""

from alembic import op


revision = "0008_plat_mfa_rc_hash_ix"
down_revision = "0007_platform_mfa_recovery_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_platform_mfa_recovery_user_codehash",
        "platform_mfa_recovery_codes",
        ["user_id", "code_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_platform_mfa_recovery_user_codehash", table_name="platform_mfa_recovery_codes")
