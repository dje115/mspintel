"""Connector framework foundation and canonical source mappings.

Revision ID: 0011_connector_foundation
Revises: 0010_ai_task_runs_exec
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_connector_foundation"
down_revision = "0010_ai_task_runs_exec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # source_system_connections: tenant-scoped connector runtime metadata
    op.add_column("source_system_connections", sa.Column("provider_family", sa.String(length=50), nullable=True))
    op.add_column("source_system_connections", sa.Column("base_url", sa.String(length=500), nullable=True))
    op.add_column("source_system_connections", sa.Column("auth_mode", sa.String(length=40), nullable=True))
    op.add_column("source_system_connections", sa.Column("encrypted_config", sa.Text(), nullable=True))
    op.add_column(
        "source_system_connections",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("source_system_connections", sa.Column("health_status", sa.String(length=20), nullable=True))
    op.add_column("source_system_connections", sa.Column("test_status", sa.String(length=20), nullable=True))
    op.add_column("source_system_connections", sa.Column("test_message", sa.Text(), nullable=True))
    op.add_column("source_system_connections", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("source_system_connections", sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "source_system_connections",
        sa.Column("last_attempted_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "source_system_connections",
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "source_system_connections",
        sa.Column("last_failed_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "source_system_connections",
        sa.Column("sync_cadence_minutes", sa.Integer(), nullable=False, server_default="60"),
    )
    op.add_column("source_system_connections", sa.Column("sync_mode", sa.String(length=20), nullable=True))
    op.add_column("source_system_connections", sa.Column("connector_version", sa.String(length=40), nullable=True))
    op.add_column("source_system_connections", sa.Column("connection_metadata", sa.JSON(), nullable=True))
    op.create_index(
        "ix_source_system_connections_tenant_system",
        "source_system_connections",
        ["tenant_id", "system_type"],
    )

    op.execute(
        "UPDATE source_system_connections SET provider_family = system_type, auth_mode = 'api_key', "
        "health_status = COALESCE(status, 'unknown'), sync_mode = 'manual_and_scheduled', connector_version = 'v1'"
    )
    op.alter_column("source_system_connections", "provider_family", nullable=False)
    op.alter_column("source_system_connections", "auth_mode", nullable=False)
    op.alter_column("source_system_connections", "health_status", nullable=False)
    op.alter_column("source_system_connections", "sync_mode", nullable=False)
    op.alter_column("source_system_connections", "connector_version", nullable=False)

    # integration_sync_runs: richer run lineage for ingestion orchestration
    op.add_column("integration_sync_runs", sa.Column("trigger_mode", sa.String(length=20), nullable=True))
    op.add_column("integration_sync_runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("integration_sync_runs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("integration_sync_runs", sa.Column("error_summary", sa.Text(), nullable=True))
    op.add_column("integration_sync_runs", sa.Column("sync_cursor", sa.String(length=120), nullable=True))
    op.add_column("integration_sync_runs", sa.Column("stats_json", sa.JSON(), nullable=True))
    op.execute("UPDATE integration_sync_runs SET trigger_mode = 'manual'")
    op.alter_column("integration_sync_runs", "trigger_mode", nullable=False)
    op.create_index(
        "ix_integration_sync_runs_tenant_conn_started",
        "integration_sync_runs",
        ["tenant_id", "source_connection_id", "started_at"],
    )

    # canonical mapping table (provider agnostic)
    op.create_table(
        "source_entity_mappings",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "source_connection_id",
            sa.Uuid(),
            sa.ForeignKey("source_system_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=180), nullable=False),
        sa.Column("canonical_entity_id", sa.Uuid(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mapping_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "source_connection_id",
            "entity_type",
            "source_id",
            name="uq_source_entity_mapping_key",
        ),
    )
    op.create_index(
        "ix_source_entity_mapping_tenant_type",
        "source_entity_mappings",
        ["tenant_id", "entity_type"],
    )

    # canonical entities: optional source refs for idempotent upserts
    op.add_column("customers", sa.Column("external_ref", sa.String(length=180), nullable=True))
    op.add_column("contacts", sa.Column("external_ref", sa.String(length=180), nullable=True))
    op.add_column("tickets", sa.Column("subject", sa.String(length=240), nullable=True))
    op.add_column("tickets", sa.Column("external_ref", sa.String(length=180), nullable=True))
    op.add_column("opportunities", sa.Column("title", sa.String(length=200), nullable=True))
    op.add_column("opportunities", sa.Column("value_cents", sa.Integer(), nullable=True))
    op.add_column("opportunities", sa.Column("external_ref", sa.String(length=180), nullable=True))
    op.add_column("quotes", sa.Column("title", sa.String(length=200), nullable=True))
    op.add_column("quotes", sa.Column("value_cents", sa.Integer(), nullable=True))
    op.add_column("quotes", sa.Column("source_system", sa.String(length=60), nullable=True))
    op.add_column("quotes", sa.Column("external_ref", sa.String(length=180), nullable=True))
    op.create_index("ix_customers_external_ref", "customers", ["external_ref"])
    op.create_index("ix_contacts_external_ref", "contacts", ["external_ref"])
    op.create_index("ix_tickets_external_ref", "tickets", ["external_ref"])
    op.create_index("ix_opportunities_external_ref", "opportunities", ["external_ref"])
    op.create_index("ix_quotes_external_ref", "quotes", ["external_ref"])


def downgrade() -> None:
    op.drop_index("ix_quotes_external_ref", table_name="quotes")
    op.drop_index("ix_opportunities_external_ref", table_name="opportunities")
    op.drop_index("ix_tickets_external_ref", table_name="tickets")
    op.drop_index("ix_contacts_external_ref", table_name="contacts")
    op.drop_index("ix_customers_external_ref", table_name="customers")
    op.drop_column("quotes", "external_ref")
    op.drop_column("quotes", "source_system")
    op.drop_column("quotes", "value_cents")
    op.drop_column("quotes", "title")
    op.drop_column("opportunities", "external_ref")
    op.drop_column("opportunities", "value_cents")
    op.drop_column("opportunities", "title")
    op.drop_column("tickets", "external_ref")
    op.drop_column("tickets", "subject")
    op.drop_column("contacts", "external_ref")
    op.drop_column("customers", "external_ref")

    op.drop_index("ix_source_entity_mapping_tenant_type", table_name="source_entity_mappings")
    op.drop_table("source_entity_mappings")

    op.drop_index("ix_integration_sync_runs_tenant_conn_started", table_name="integration_sync_runs")
    op.drop_column("integration_sync_runs", "stats_json")
    op.drop_column("integration_sync_runs", "sync_cursor")
    op.drop_column("integration_sync_runs", "error_summary")
    op.drop_column("integration_sync_runs", "completed_at")
    op.drop_column("integration_sync_runs", "started_at")
    op.drop_column("integration_sync_runs", "trigger_mode")

    op.drop_index("ix_source_system_connections_tenant_system", table_name="source_system_connections")
    op.drop_column("source_system_connections", "connection_metadata")
    op.drop_column("source_system_connections", "connector_version")
    op.drop_column("source_system_connections", "sync_mode")
    op.drop_column("source_system_connections", "sync_cadence_minutes")
    op.drop_column("source_system_connections", "last_failed_sync_at")
    op.drop_column("source_system_connections", "last_successful_sync_at")
    op.drop_column("source_system_connections", "last_attempted_sync_at")
    op.drop_column("source_system_connections", "last_tested_at")
    op.drop_column("source_system_connections", "last_error")
    op.drop_column("source_system_connections", "test_message")
    op.drop_column("source_system_connections", "test_status")
    op.drop_column("source_system_connections", "health_status")
    op.drop_column("source_system_connections", "is_enabled")
    op.drop_column("source_system_connections", "encrypted_config")
    op.drop_column("source_system_connections", "auth_mode")
    op.drop_column("source_system_connections", "base_url")
    op.drop_column("source_system_connections", "provider_family")
