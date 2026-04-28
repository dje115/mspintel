"""tenant profile and service catalogue

Revision ID: 0018_tenant_profile_v2
Revises: 0017_m365_slice_v2
Create Date: 2026-04-27 17:12:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0018_tenant_profile_v2"
down_revision: str | None = "0017_m365_slice_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "tenant_msp_profiles" not in tables:
        op.create_table(
            "tenant_msp_profiles",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("legal_name", sa.String(length=220), nullable=True),
            sa.Column("brand_name", sa.String(length=220), nullable=True),
            sa.Column("regions_served", sa.JSON(), nullable=True),
            sa.Column("vertical_focus", sa.JSON(), nullable=True),
            sa.Column("team_size_band", sa.String(length=60), nullable=True),
            sa.Column("customer_count_band", sa.String(length=60), nullable=True),
            sa.Column("typical_customer_size_band", sa.String(length=60), nullable=True),
            sa.Column("delivery_model", sa.String(length=120), nullable=True),
            sa.Column("business_goals", sa.JSON(), nullable=True),
            sa.Column("free_text_description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_id", name="uq_tenant_msp_profile_tenant"),
        )
    idx_names = {i["name"] for i in inspector.get_indexes("tenant_msp_profiles")} if "tenant_msp_profiles" in set(inspector.get_table_names()) else set()
    if "ix_tenant_msp_profiles_tenant" not in idx_names:
        op.create_index("ix_tenant_msp_profiles_tenant", "tenant_msp_profiles", ["tenant_id"])

    tables = set(sa.inspect(bind).get_table_names())
    if "tenant_service_catalog_entries" not in tables:
        op.create_table(
            "tenant_service_catalog_entries",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("service_key", sa.String(length=80), nullable=False),
            sa.Column("service_name", sa.String(length=160), nullable=False),
            sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_id", "service_key", name="uq_tenant_service_catalog_tenant_key"),
        )
    idx_names = {i["name"] for i in sa.inspect(bind).get_indexes("tenant_service_catalog_entries")} if "tenant_service_catalog_entries" in set(sa.inspect(bind).get_table_names()) else set()
    if "ix_tenant_service_catalog_tenant" not in idx_names:
        op.create_index("ix_tenant_service_catalog_tenant", "tenant_service_catalog_entries", ["tenant_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "tenant_service_catalog_entries" in tables:
        idx_names = {i["name"] for i in inspector.get_indexes("tenant_service_catalog_entries")}
        if "ix_tenant_service_catalog_tenant" in idx_names:
            op.drop_index("ix_tenant_service_catalog_tenant", table_name="tenant_service_catalog_entries")
        op.drop_table("tenant_service_catalog_entries")
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "tenant_msp_profiles" in tables:
        idx_names = {i["name"] for i in inspector.get_indexes("tenant_msp_profiles")}
        if "ix_tenant_msp_profiles_tenant" in idx_names:
            op.drop_index("ix_tenant_msp_profiles_tenant", table_name="tenant_msp_profiles")
        op.drop_table("tenant_msp_profiles")

