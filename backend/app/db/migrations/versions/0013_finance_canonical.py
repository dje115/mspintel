"""Canonical finance / billing slice (Phase 0) for intelligence surfaces.

Revision ID: 0013_finance_canonical
Revises: 0012_customer_demo_profile
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_finance_canonical"
down_revision = "0012_customer_demo_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finance_billing_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "customer_id",
            sa.Uuid(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "source_connection_id",
            sa.Uuid(),
            sa.ForeignKey("source_system_connections.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("external_billing_account_id", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=220), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=True),
        sa.Column("linkage_status", sa.String(length=40), nullable=False, server_default="linked"),
        sa.Column("coverage_notes", sa.Text(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_billing_account_id", name="uq_finance_billing_account_ext"),
    )
    op.create_index(
        "ix_finance_billing_accounts_tenant_customer",
        "finance_billing_accounts",
        ["tenant_id", "customer_id"],
    )

    op.create_table(
        "finance_invoices",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "billing_account_id",
            sa.Uuid(),
            sa.ForeignKey("finance_billing_accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_connection_id",
            sa.Uuid(),
            sa.ForeignKey("source_system_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_invoice_id", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outstanding_cents", sa.Integer(), nullable=True),
        sa.Column("currency_code", sa.String(length=12), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "billing_account_id",
            "external_invoice_id",
            name="uq_finance_invoice_per_account",
        ),
    )

    op.create_table(
        "finance_billing_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "billing_account_id",
            sa.Uuid(),
            sa.ForeignKey("finance_billing_accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_connection_id",
            sa.Uuid(),
            sa.ForeignKey("source_system_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("billed_users", sa.Integer(), nullable=True),
        sa.Column("billed_mailboxes", sa.Integer(), nullable=True),
        sa.Column("billed_devices", sa.Integer(), nullable=True),
        sa.Column("billed_storage_tb", sa.Numeric(14, 4), nullable=True),
        sa.Column("service_licensed_users", sa.Integer(), nullable=True),
        sa.Column("service_active_mailboxes", sa.Integer(), nullable=True),
        sa.Column("mrr_cents", sa.Integer(), nullable=True),
        sa.Column("payment_status_summary", sa.String(length=80), nullable=True),
        sa.Column("aged_outstanding_cents", sa.Integer(), nullable=True),
        sa.Column("confidence_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("coverage_notes", sa.Text(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_finance_snapshots_account_effective",
        "finance_billing_snapshots",
        ["billing_account_id", "effective_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_finance_snapshots_account_effective", table_name="finance_billing_snapshots")
    op.drop_table("finance_billing_snapshots")
    op.drop_table("finance_invoices")
    op.drop_index("ix_finance_billing_accounts_tenant_customer", table_name="finance_billing_accounts")
    op.drop_table("finance_billing_accounts")
