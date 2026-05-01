"""backup protection facts for BCDR connectors

Revision ID: 0021_backup_protection_facts
Revises: 0020_xero_invoice_lines
Create Date: 2026-04-30 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0021_backup_protection_facts"
down_revision: str | None = "0020_xero_invoice_lines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "backup_protection_facts" in tables:
        return
    op.create_table(
        "backup_protection_facts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "source_connection_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("source_system_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vendor_system_type", sa.String(length=40), nullable=False),
        sa.Column("fact_kind", sa.String(length=40), nullable=False),
        sa.Column("source_external_id", sa.String(length=200), nullable=False),
        sa.Column("source_customer_external_id", sa.String(length=120), nullable=True),
        sa.Column("customer_id", sa.Uuid(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("display_name", sa.String(length=240), nullable=True),
        sa.Column("health_status", sa.String(length=40), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("signals_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "source_connection_id",
            "fact_kind",
            "source_external_id",
            name="uq_backup_fact_per_connection",
        ),
    )
    op.create_index("ix_backup_facts_tenant_customer", "backup_protection_facts", ["tenant_id", "customer_id"])


def downgrade() -> None:
    op.drop_index("ix_backup_facts_tenant_customer", table_name="backup_protection_facts")
    op.drop_table("backup_protection_facts")
