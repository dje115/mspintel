"""m365 slice v1 canonical posture table

Revision ID: 0015_m365_slice_v1
Revises: 0014_risk_engine_v1
Create Date: 2026-04-27 15:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0015_m365_slice_v1"
down_revision: str | None = "0014_risk_engine_v1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "m365_customer_postures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(), nullable=True),
        sa.Column("external_tenant_ref", sa.String(length=180), nullable=True),
        sa.Column("tenant_display_name", sa.String(length=200), nullable=True),
        sa.Column("domain_name", sa.String(length=200), nullable=True),
        sa.Column("licensed_users", sa.Integer(), nullable=True),
        sa.Column("active_users_30d", sa.Integer(), nullable=True),
        sa.Column("inactive_users_30d", sa.Integer(), nullable=True),
        sa.Column("mailbox_count", sa.Integer(), nullable=True),
        sa.Column("shared_mailbox_count", sa.Integer(), nullable=True),
        sa.Column("unused_licences", sa.Integer(), nullable=True),
        sa.Column("mfa_coverage_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("licence_summary_json", sa.JSON(), nullable=True),
        sa.Column("hygiene_findings", sa.JSON(), nullable=True),
        sa.Column("optimisation_findings", sa.JSON(), nullable=True),
        sa.Column("confidence_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("coverage_notes", sa.Text(), nullable=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_connection_id"], ["source_system_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "customer_id", name="uq_m365_customer_posture_tenant_customer"),
    )
    op.create_index(
        "ix_m365_customer_postures_tenant_measured",
        "m365_customer_postures",
        ["tenant_id", "measured_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_m365_customer_postures_tenant_measured", table_name="m365_customer_postures")
    op.drop_table("m365_customer_postures")

