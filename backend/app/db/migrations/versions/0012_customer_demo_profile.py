"""Optional JSON demo profile per customer (synthetic UK MSP scenarios for seed/AI).

Revision ID: 0012_customer_demo_profile
Revises: 0011_connector_foundation
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_customer_demo_profile"
down_revision = "0011_connector_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("demo_profile", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "demo_profile")
