"""Risk Engine v1 snapshot metadata on account_scores.

Revision ID: 0014_risk_engine_v1
Revises: 0013_finance_canonical
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_risk_engine_v1"
down_revision = "0013_finance_canonical"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("account_scores", sa.Column("risk_level", sa.String(length=20), nullable=True))
    op.add_column("account_scores", sa.Column("attention_level", sa.String(length=20), nullable=True))
    op.add_column("account_scores", sa.Column("confidence_level", sa.String(length=20), nullable=True))
    op.add_column("account_scores", sa.Column("scoring_version", sa.String(length=40), nullable=True))
    op.add_column("account_scores", sa.Column("reason_codes", sa.JSON(), nullable=True))
    op.add_column("account_scores", sa.Column("factors_json", sa.JSON(), nullable=True))
    op.add_column("account_scores", sa.Column("coverage_notes", sa.JSON(), nullable=True))
    op.add_column("account_scores", sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE account_scores SET risk_level='low', attention_level='low', confidence_level='medium', "
        "scoring_version='risk_v1', calculated_at=COALESCE(created_at, now())"
    )
    op.alter_column("account_scores", "risk_level", nullable=False)
    op.alter_column("account_scores", "attention_level", nullable=False)
    op.alter_column("account_scores", "confidence_level", nullable=False)
    op.alter_column("account_scores", "scoring_version", nullable=False)
    op.alter_column(
        "account_scores",
        "calculated_at",
        nullable=False,
        server_default=sa.text("now()"),
    )
    op.create_index("ix_account_scores_tenant_customer_calc", "account_scores", ["tenant_id", "customer_id", "calculated_at"])


def downgrade() -> None:
    op.drop_index("ix_account_scores_tenant_customer_calc", table_name="account_scores")
    op.drop_column("account_scores", "calculated_at")
    op.drop_column("account_scores", "coverage_notes")
    op.drop_column("account_scores", "factors_json")
    op.drop_column("account_scores", "reason_codes")
    op.drop_column("account_scores", "scoring_version")
    op.drop_column("account_scores", "confidence_level")
    op.drop_column("account_scores", "attention_level")
    op.drop_column("account_scores", "risk_level")
