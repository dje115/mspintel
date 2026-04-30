"""xero thin import invoice lines

Revision ID: 0020_xero_invoice_lines
Revises: 0019_cust_rev_ai_artifact
Create Date: 2026-04-30 07:55:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0020_xero_invoice_lines"
down_revision: str | None = "0019_cust_rev_ai_artifact"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "finance_invoice_lines" not in tables:
        op.create_table(
            "finance_invoice_lines",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("invoice_id", sa.Uuid(as_uuid=True), sa.ForeignKey("finance_invoices.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "source_connection_id",
                sa.Uuid(as_uuid=True),
                sa.ForeignKey("source_system_connections.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("external_line_id", sa.String(length=200), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("quantity", sa.Numeric(14, 4), nullable=True),
            sa.Column("unit_amount_cents", sa.Integer(), nullable=True),
            sa.Column("line_total_cents", sa.Integer(), nullable=True),
            sa.Column("tax_amount_cents", sa.Integer(), nullable=True),
            sa.Column("account_code", sa.String(length=80), nullable=True),
            sa.Column("extra", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "invoice_id", "external_line_id", name="uq_finance_invoice_line_per_invoice"),
        )
        op.create_index("ix_finance_invoice_lines_invoice", "finance_invoice_lines", ["invoice_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "finance_invoice_lines" in tables:
        op.drop_index("ix_finance_invoice_lines_invoice", table_name="finance_invoice_lines")
        op.drop_table("finance_invoice_lines")
