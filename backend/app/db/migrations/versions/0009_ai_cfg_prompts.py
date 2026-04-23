"""AI provider catalog, tenant AI settings/task routes, prompts + versions, task run lineage.

Revision ID: 0009_ai_cfg_prompts
Revises: 0008_plat_mfa_rc_hash_ix
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_ai_cfg_prompts"
down_revision = "0008_plat_mfa_rc_hash_ix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_catalog",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("provider_family", sa.String(length=80), nullable=False),
        sa.Column("deployment_mode", sa.String(length=40), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_ai_provider_catalog_code"),
    )
    op.create_index("ix_ai_provider_catalog_family_mode", "ai_provider_catalog", ["provider_family", "deployment_mode"])

    op.add_column("ai_providers", sa.Column("catalog_code", sa.String(length=80), nullable=True))
    op.add_column("ai_providers", sa.Column("provider_family", sa.String(length=80), nullable=True))
    op.add_column("ai_providers", sa.Column("deployment_mode", sa.String(length=40), nullable=True))
    op.add_column("ai_providers", sa.Column("display_label", sa.String(length=200), nullable=True))
    op.add_column("ai_providers", sa.Column("base_url", sa.String(length=500), nullable=True))
    op.add_column("ai_providers", sa.Column("encrypted_settings", sa.Text(), nullable=True))
    op.add_column("ai_providers", sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_ai_providers_catalog_code", "ai_providers", ["catalog_code"])
    op.create_index("ix_ai_providers_family_mode", "ai_providers", ["provider_family", "deployment_mode"])

    op.create_table(
        "prompt_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("prompt_key", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prompt_definitions_tenant", "prompt_definitions", ["tenant_id"])
    op.create_index("ix_prompt_definitions_key", "prompt_definitions", ["prompt_key"])
    op.create_index("ix_prompt_definitions_scope_tenant_key", "prompt_definitions", ["scope", "tenant_id", "prompt_key"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("prompt_definition_id", sa.Uuid(), sa.ForeignKey("prompt_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prompt_versions_def", "prompt_versions", ["prompt_definition_id"])
    op.create_index("ix_prompt_versions_def_active", "prompt_versions", ["prompt_definition_id", "is_active"])

    op.create_table(
        "prompt_activation_events",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("prompt_definition_id", sa.Uuid(), sa.ForeignKey("prompt_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_version_id", sa.Uuid(), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_kind", sa.String(length=40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prompt_activation_def", "prompt_activation_events", ["prompt_definition_id"])

    op.create_table(
        "tenant_ai_settings",
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("default_ai_provider_id", sa.Uuid(), sa.ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("default_model", sa.String(length=200), nullable=True),
        sa.Column("fallback_ai_provider_id", sa.Uuid(), sa.ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fallback_model", sa.String(length=200), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "tenant_ai_task_routes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("ai_provider_id", sa.Uuid(), sa.ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("fallback_ai_provider_id", sa.Uuid(), sa.ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fallback_model", sa.String(length=200), nullable=True),
        sa.Column("prompt_key", sa.String(length=160), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "task_type", name="uq_tenant_ai_task_route"),
    )
    op.create_index("ix_tenant_ai_task_routes_tenant", "tenant_ai_task_routes", ["tenant_id"])

    op.add_column("ai_task_runs", sa.Column("provider_family", sa.String(length=80), nullable=True))
    op.add_column("ai_task_runs", sa.Column("deployment_mode", sa.String(length=40), nullable=True))
    op.add_column("ai_task_runs", sa.Column("model_used", sa.String(length=200), nullable=True))
    op.add_column("ai_task_runs", sa.Column("ai_provider_id", sa.Uuid(), sa.ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True))
    op.add_column("ai_task_runs", sa.Column("prompt_definition_id", sa.Uuid(), sa.ForeignKey("prompt_definitions.id", ondelete="SET NULL"), nullable=True))
    op.add_column("ai_task_runs", sa.Column("prompt_version_id", sa.Uuid(), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True))
    op.add_column("ai_task_runs", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("ai_task_runs", sa.Column("run_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_task_runs", "run_metadata")
    op.drop_column("ai_task_runs", "duration_ms")
    op.drop_column("ai_task_runs", "prompt_version_id")
    op.drop_column("ai_task_runs", "prompt_definition_id")
    op.drop_column("ai_task_runs", "ai_provider_id")
    op.drop_column("ai_task_runs", "model_used")
    op.drop_column("ai_task_runs", "deployment_mode")
    op.drop_column("ai_task_runs", "provider_family")

    op.drop_index("ix_tenant_ai_task_routes_tenant", table_name="tenant_ai_task_routes")
    op.drop_table("tenant_ai_task_routes")

    op.drop_table("tenant_ai_settings")

    op.drop_index("ix_prompt_activation_def", table_name="prompt_activation_events")
    op.drop_table("prompt_activation_events")

    op.drop_index("ix_prompt_versions_def_active", table_name="prompt_versions")
    op.drop_index("ix_prompt_versions_def", table_name="prompt_versions")
    op.drop_table("prompt_versions")

    op.drop_index("ix_prompt_definitions_scope_tenant_key", table_name="prompt_definitions")
    op.drop_index("ix_prompt_definitions_key", table_name="prompt_definitions")
    op.drop_index("ix_prompt_definitions_tenant", table_name="prompt_definitions")
    op.drop_table("prompt_definitions")

    op.drop_index("ix_ai_providers_family_mode", table_name="ai_providers")
    op.drop_index("ix_ai_providers_catalog_code", table_name="ai_providers")
    op.drop_column("ai_providers", "is_enabled")
    op.drop_column("ai_providers", "encrypted_settings")
    op.drop_column("ai_providers", "base_url")
    op.drop_column("ai_providers", "display_label")
    op.drop_column("ai_providers", "deployment_mode")
    op.drop_column("ai_providers", "provider_family")
    op.drop_column("ai_providers", "catalog_code")

    op.drop_index("ix_ai_provider_catalog_family_mode", table_name="ai_provider_catalog")
    op.drop_table("ai_provider_catalog")
