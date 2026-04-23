"""create saas core schema

Revision ID: 0001_saas_core
Revises: 
Create Date: 2026-04-23 12:20:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_saas_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "tenant_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),
    )
    op.create_index("ix_membership_tenant", "tenant_memberships", ["tenant_id"])
    op.create_index("ix_membership_user", "tenant_memberships", ["user_id"])

    op.create_table(
        "tenant_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("price_monthly_cents", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_plans_code"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="trial"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "onboarding_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("step", sa.String(length=60), nullable=False, server_default="welcome"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # tenant-owned operational/business tables
    for table_name, extra_cols in [
        ("source_system_connections", [sa.Column("system_type", sa.String(length=50), nullable=False), sa.Column("display_name", sa.String(length=120), nullable=False), sa.Column("status", sa.String(length=20), nullable=False), sa.Column("last_sync_at", sa.DateTime(timezone=True))]),
        ("integration_sync_runs", [sa.Column("source_connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("source_system_connections.id"), nullable=False), sa.Column("status", sa.String(length=20), nullable=False), sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0")]),
        ("customers", [sa.Column("name", sa.String(length=180), nullable=False), sa.Column("status", sa.String(length=30), nullable=False, server_default="active"), sa.Column("owner_name", sa.String(length=120))]),
        ("contacts", [sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("email", sa.String(length=320))]),
        ("tickets", [sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False), sa.Column("status", sa.String(length=30), nullable=False, server_default="open")]),
        ("opportunities", [sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False), sa.Column("status", sa.String(length=30), nullable=False, server_default="open")]),
        ("quotes", [sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False), sa.Column("status", sa.String(length=30), nullable=False, server_default="draft")]),
        ("account_scores", [sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False), sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"), sa.Column("attention_score", sa.Integer(), nullable=False, server_default="0"), sa.Column("growth_score", sa.Integer(), nullable=False, server_default="0")]),
        ("recommendations", [sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id")), sa.Column("scope", sa.String(length=30), nullable=False, server_default="executive"), sa.Column("status", sa.String(length=30), nullable=False, server_default="open"), sa.Column("summary", sa.String(length=280), nullable=False)]),
        ("actions", [sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id")), sa.Column("description", sa.String(length=280), nullable=False)]),
        ("ai_providers", [sa.Column("provider_name", sa.String(length=60), nullable=False), sa.Column("status", sa.String(length=20), nullable=False, server_default="configured")]),
        ("ai_model_configs", [sa.Column("ai_provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_providers.id"), nullable=False), sa.Column("model_name", sa.String(length=100), nullable=False), sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false())]),
        ("ai_task_runs", [sa.Column("task_type", sa.String(length=80), nullable=False), sa.Column("status", sa.String(length=20), nullable=False, server_default="queued")]),
        ("audit_events", [sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")), sa.Column("event_type", sa.String(length=80), nullable=False), sa.Column("details", sa.Text())]),
    ]:
        cols = [
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            *extra_cols,
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        ]
        op.create_table(table_name, *cols)
        op.create_index(f"ix_{table_name}_tenant", table_name, ["tenant_id"])


def downgrade() -> None:
    for table_name in [
        "audit_events",
        "ai_task_runs",
        "ai_model_configs",
        "ai_providers",
        "actions",
        "recommendations",
        "account_scores",
        "quotes",
        "opportunities",
        "tickets",
        "contacts",
        "customers",
        "integration_sync_runs",
        "source_system_connections",
        "onboarding_states",
        "subscriptions",
        "plans",
        "tenant_settings",
        "tenant_memberships",
        "role_permissions",
        "permissions",
        "roles",
        "tenants",
        "users",
    ]:
        op.drop_table(table_name)
