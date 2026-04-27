"""m365 slice v2 enrichment

Revision ID: 0017_m365_slice_v2
Revises: 0016_onboarding_ctrls
Create Date: 2026-04-27 16:40:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0017_m365_slice_v2"
down_revision: str | None = "0016_onboarding_ctrls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("m365_customer_postures")}
    if "disabled_users" not in existing:
        op.add_column("m365_customer_postures", sa.Column("disabled_users", sa.Integer(), nullable=True))
    if "stale_users_90d" not in existing:
        op.add_column("m365_customer_postures", sa.Column("stale_users_90d", sa.Integer(), nullable=True))
    if "privileged_admin_users" not in existing:
        op.add_column("m365_customer_postures", sa.Column("privileged_admin_users", sa.Integer(), nullable=True))
    if "tenant_domains_json" not in existing:
        op.add_column("m365_customer_postures", sa.Column("tenant_domains_json", sa.JSON(), nullable=True))
    if "usage_summary_json" not in existing:
        op.add_column("m365_customer_postures", sa.Column("usage_summary_json", sa.JSON(), nullable=True))
    if "entra_summary_json" not in existing:
        op.add_column("m365_customer_postures", sa.Column("entra_summary_json", sa.JSON(), nullable=True))
    if "azure_summary_json" not in existing:
        op.add_column("m365_customer_postures", sa.Column("azure_summary_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("m365_customer_postures")}
    if "azure_summary_json" in existing:
        op.drop_column("m365_customer_postures", "azure_summary_json")
    if "entra_summary_json" in existing:
        op.drop_column("m365_customer_postures", "entra_summary_json")
    if "usage_summary_json" in existing:
        op.drop_column("m365_customer_postures", "usage_summary_json")
    if "tenant_domains_json" in existing:
        op.drop_column("m365_customer_postures", "tenant_domains_json")
    if "privileged_admin_users" in existing:
        op.drop_column("m365_customer_postures", "privileged_admin_users")
    if "stale_users_90d" in existing:
        op.drop_column("m365_customer_postures", "stale_users_90d")
    if "disabled_users" in existing:
        op.drop_column("m365_customer_postures", "disabled_users")

