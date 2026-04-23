"""AI task run execution metadata (timing, errors, context FKs, fallback flag).

Revision ID: 0010_ai_task_runs_exec
Revises: 0009_ai_cfg_prompts
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_ai_task_runs_exec"
down_revision = "0009_ai_cfg_prompts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_task_runs", sa.Column("error_summary", sa.Text(), nullable=True))
    op.add_column("ai_task_runs", sa.Column("output_summary", sa.Text(), nullable=True))
    op.add_column("ai_task_runs", sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("ai_task_runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_task_runs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "ai_task_runs",
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "ai_task_runs",
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "ai_task_runs",
        sa.Column("recommendation_id", sa.Uuid(), sa.ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_ai_task_runs_customer", "ai_task_runs", ["tenant_id", "customer_id"])
    op.create_index("ix_ai_task_runs_rec", "ai_task_runs", ["tenant_id", "recommendation_id"])
    op.create_index("ix_ai_task_runs_status", "ai_task_runs", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_ai_task_runs_status", table_name="ai_task_runs")
    op.drop_index("ix_ai_task_runs_rec", table_name="ai_task_runs")
    op.drop_index("ix_ai_task_runs_customer", table_name="ai_task_runs")
    op.drop_column("ai_task_runs", "recommendation_id")
    op.drop_column("ai_task_runs", "customer_id")
    op.drop_column("ai_task_runs", "actor_user_id")
    op.drop_column("ai_task_runs", "completed_at")
    op.drop_column("ai_task_runs", "started_at")
    op.drop_column("ai_task_runs", "fallback_used")
    op.drop_column("ai_task_runs", "output_summary")
    op.drop_column("ai_task_runs", "error_summary")
