"""connector onboarding controls and mapping review

Revision ID: 0016_onboarding_ctrls
Revises: 0015_m365_slice_v1
Create Date: 2026-04-27 15:55:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0016_onboarding_ctrls"
down_revision: str | None = "0015_m365_slice_v1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_system_connections", sa.Column("lifecycle_state", sa.String(length=40), nullable=False, server_default="configured"))
    op.add_column(
        "source_system_connections",
        sa.Column("sync_behavior", sa.String(length=40), nullable=False, server_default="manual_sync_only"),
    )
    op.add_column("source_system_connections", sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("source_system_connections", sa.Column("import_scope_mode", sa.String(length=40), nullable=False, server_default="all"))
    op.add_column("source_system_connections", sa.Column("import_scope_filters", sa.JSON(), nullable=True))
    op.add_column("source_system_connections", sa.Column("last_lifecycle_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source_system_connections", sa.Column("last_lifecycle_note", sa.Text(), nullable=True))

    op.create_table(
        "connector_mapping_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("source_external_id", sa.String(length=240), nullable=False),
        sa.Column("source_display_name", sa.String(length=240), nullable=True),
        sa.Column("source_domain", sa.String(length=200), nullable=True),
        sa.Column("suggested_customer_id", sa.Uuid(), nullable=True),
        sa.Column("suggested_confidence", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("suggested_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("suggested_reasons", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("mapped_customer_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_connection_id"], ["source_system_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["suggested_customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mapped_customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "source_connection_id", "entity_type", "source_external_id", name="uq_connector_mapping_review_key"
        ),
    )
    op.create_index(
        "ix_connector_mapping_reviews_tenant_status",
        "connector_mapping_reviews",
        ["tenant_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_connector_mapping_reviews_tenant_status", table_name="connector_mapping_reviews")
    op.drop_table("connector_mapping_reviews")

    op.drop_column("source_system_connections", "last_lifecycle_note")
    op.drop_column("source_system_connections", "last_lifecycle_changed_at")
    op.drop_column("source_system_connections", "import_scope_filters")
    op.drop_column("source_system_connections", "import_scope_mode")
    op.drop_column("source_system_connections", "is_paused")
    op.drop_column("source_system_connections", "sync_behavior")
    op.drop_column("source_system_connections", "lifecycle_state")

