"""customer review AI artefacts persistence

Revision ID: 0019_cust_rev_ai_artifact
Revises: 0018_tenant_profile_v2
Create Date: 2026-04-29 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0019_cust_rev_ai_artifact"
down_revision: str | None = "0018_tenant_profile_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "customer_review_ai_artifacts" in tables:
        return
    op.create_table(
        "customer_review_ai_artifacts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Uuid(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="succeeded"),
        sa.Column("full_output_json", sa.JSON(), nullable=True),
        sa.Column("full_output_text", sa.Text(), nullable=True),
        sa.Column("short_context_json", sa.JSON(), nullable=True),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "ai_task_run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("ai_task_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("prompt_key", sa.String(length=200), nullable=True),
        sa.Column(
            "prompt_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider_family", sa.String(length=80), nullable=True),
        sa.Column("deployment_mode", sa.String(length=40), nullable=True),
        sa.Column("model_used", sa.String(length=200), nullable=True),
        sa.Column("source_data_version", sa.String(length=120), nullable=True),
        sa.Column("source_coverage_summary", sa.JSON(), nullable=True),
        sa.Column("generated_from_connector_state", sa.JSON(), nullable=True),
        sa.Column("output_warnings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_crai_tenant_customer_created",
        "customer_review_ai_artifacts",
        ["tenant_id", "customer_id", "created_at"],
    )
    op.create_index(
        "ix_crai_tenant_customer_type_created",
        "customer_review_ai_artifacts",
        ["tenant_id", "customer_id", "artifact_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_crai_tenant_customer_type_created", table_name="customer_review_ai_artifacts")
    op.drop_index("ix_crai_tenant_customer_created", table_name="customer_review_ai_artifacts")
    op.drop_table("customer_review_ai_artifacts")
