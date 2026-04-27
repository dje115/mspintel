import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class UserMfaMethod(Base, TimestampMixin):
    """Second-factor methods for a user (platform TOTP today; WebAuthn metadata reserved)."""

    __tablename__ = "user_mfa_methods"
    __table_args__ = (UniqueConstraint("user_id", "method_type", name="uq_user_mfa_method_type"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    method_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    method_label: Mapped[str] = mapped_column(String(120), default="Authenticator app")
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    method_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlatformMfaRecoveryCode(Base, TimestampMixin):
    """One-time platform MFA recovery codes (hashed at rest; platform operators only)."""

    __tablename__ = "platform_mfa_recovery_codes"
    __table_args__ = (
        Index("ix_platform_mfa_recovery_user_unused", "user_id", "is_used"),
        Index("ix_platform_mfa_recovery_user_batch", "user_id", "batch_id"),
        Index("ix_platform_mfa_recovery_user_codehash", "user_id", "code_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(String(200))


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class TenantMembership(Base, TimestampMixin):
    __tablename__ = "tenant_memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("roles.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")


class TenantInvitation(Base, TimestampMixin):
    __tablename__ = "tenant_invitations"
    __table_args__ = (Index("ix_tenant_invitations_email_status", "email", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    role_to_assign: Mapped[str] = mapped_column(String(50))
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_revoked", "user_id", "revoked_at"),
        Index("ix_user_sessions_user_auth", "user_id", "auth_mode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    device_label: Mapped[str | None] = mapped_column(String(200))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auth_mode: Mapped[str] = mapped_column(String(16), default="tenant", server_default="tenant")


class TenantSetting(Base, TimestampMixin):
    __tablename__ = "tenant_settings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(120))
    value: Mapped[str] = mapped_column(Text)


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    price_monthly_cents: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("plans.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="trial")


class OnboardingState(Base, TimestampMixin):
    __tablename__ = "onboarding_states"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="pending")
    step: Mapped[str] = mapped_column(String(60), default="welcome")


class SourceSystemConnection(Base, TimestampMixin):
    __tablename__ = "source_system_connections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    system_type: Mapped[str] = mapped_column(String(50))
    provider_family: Mapped[str] = mapped_column(String(50), default="generic")
    display_name: Mapped[str] = mapped_column(String(120))
    base_url: Mapped[str | None] = mapped_column(String(500))
    auth_mode: Mapped[str] = mapped_column(String(40), default="api_key")
    encrypted_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="disconnected")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")
    test_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    test_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempted_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_cadence_minutes: Mapped[int] = mapped_column(Integer, default=60)
    sync_mode: Mapped[str] = mapped_column(String(20), default="manual_and_scheduled")
    connector_version: Mapped[str] = mapped_column(String(40), default="v1")
    connection_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(String(40), default="configured")
    sync_behavior: Mapped[str] = mapped_column(String(40), default="manual_sync_only")
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    import_scope_mode: Mapped[str] = mapped_column(String(40), default="all")
    import_scope_filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_lifecycle_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_lifecycle_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntegrationSyncRun(Base, TimestampMixin):
    __tablename__ = "integration_sync_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_system_connections.id"), index=True
    )
    trigger_mode: Mapped[str] = mapped_column(String(20), default="manual")
    status: Mapped[str] = mapped_column(String(20))
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    stats_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SourceEntityMapping(Base, TimestampMixin):
    __tablename__ = "source_entity_mappings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_connection_id",
            "entity_type",
            "source_id",
            name="uq_source_entity_mapping_key",
        ),
        Index("ix_source_entity_mapping_tenant_type", "tenant_id", "entity_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_system_connections.id"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(180))
    canonical_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mapping_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ConnectorMappingReview(Base, TimestampMixin):
    __tablename__ = "connector_mapping_reviews"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_connection_id",
            "entity_type",
            "source_external_id",
            name="uq_connector_mapping_review_key",
        ),
        Index("ix_connector_mapping_reviews_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_system_connections.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(60))
    source_external_id: Mapped[str] = mapped_column(String(240))
    source_display_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    source_domain: Mapped[str | None] = mapped_column(String(200), nullable=True)
    suggested_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    suggested_confidence: Mapped[str] = mapped_column(String(20), default="low")
    suggested_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    suggested_reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    mapped_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    __table_args__ = (Index("ix_customers_tenant_status", "tenant_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    owner_name: Mapped[str | None] = mapped_column(String(120))
    external_ref: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    demo_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class FinanceBillingAccount(Base, TimestampMixin):
    """Tenant-scoped billing / finance account linked to a customer when known."""

    __tablename__ = "finance_billing_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_billing_account_id", name="uq_finance_billing_account_ext"),
        Index("ix_finance_billing_accounts_tenant_customer", "tenant_id", "customer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=True
    )
    source_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_system_connections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_billing_account_id: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(220), nullable=False)
    currency_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    linkage_status: Mapped[str] = mapped_column(String(40), default="linked", nullable=False)
    coverage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class FinanceInvoice(Base, TimestampMixin):
    __tablename__ = "finance_invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "billing_account_id", "external_invoice_id", name="uq_finance_invoice_per_account"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    billing_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("finance_billing_accounts.id", ondelete="CASCADE"), index=True
    )
    source_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_system_connections.id", ondelete="SET NULL"), nullable=True
    )
    external_invoice_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    outstanding_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class FinanceBillingSnapshot(Base, TimestampMixin):
    __tablename__ = "finance_billing_snapshots"
    __table_args__ = (Index("ix_finance_snapshots_account_effective", "billing_account_id", "effective_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    billing_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("finance_billing_accounts.id", ondelete="CASCADE"), index=True
    )
    source_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_system_connections.id", ondelete="SET NULL"), nullable=True
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    billed_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billed_mailboxes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billed_devices: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billed_storage_tb: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    service_licensed_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_active_mailboxes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mrr_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_status_summary: Mapped[str | None] = mapped_column(String(80), nullable=True)
    aged_outstanding_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    coverage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class M365CustomerPosture(Base, TimestampMixin):
    __tablename__ = "m365_customer_postures"
    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_id", name="uq_m365_customer_posture_tenant_customer"),
        Index("ix_m365_customer_postures_tenant_measured", "tenant_id", "measured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    source_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_system_connections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_tenant_ref: Mapped[str | None] = mapped_column(String(180), nullable=True)
    tenant_display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    domain_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    licensed_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_users_30d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inactive_users_30d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disabled_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stale_users_90d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    privileged_admin_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mailbox_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shared_mailbox_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unused_licences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mfa_coverage_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    tenant_domains_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    licence_summary_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    usage_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    entra_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    azure_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hygiene_findings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    optimisation_findings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    confidence_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    coverage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("customers.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(320))
    external_ref: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="open")
    subject: Mapped[str | None] = mapped_column(String(240), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="open")
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    value_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)


class Quote(Base, TimestampMixin):
    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    value_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_system: Mapped[str | None] = mapped_column(String(60), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)


class AccountScore(Base, TimestampMixin):
    __tablename__ = "account_scores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("customers.id"), index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    attention_score: Mapped[int] = mapped_column(Integer, default=0)
    growth_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    attention_level: Mapped[str] = mapped_column(String(20), default="low")
    confidence_level: Mapped[str] = mapped_column(String(20), default="medium")
    scoring_version: Mapped[str] = mapped_column(String(40), default="risk_v1")
    reason_codes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    factors_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    coverage_notes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("customers.id"))
    scope: Mapped[str] = mapped_column(String(30), default="executive")
    status: Mapped[str] = mapped_column(String(30), default="open")
    summary: Mapped[str] = mapped_column(String(280))


class Action(Base, TimestampMixin):
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("customers.id"))
    description: Mapped[str] = mapped_column(String(280))


class AIProviderCatalog(Base, TimestampMixin):
    """Platform catalog row: stable ``code`` + ``provider_family`` + ``deployment_mode`` for UI and defaults."""

    __tablename__ = "ai_provider_catalog"
    __table_args__ = (
        UniqueConstraint("code", name="uq_ai_provider_catalog_code"),
        Index("ix_ai_provider_catalog_family_mode", "provider_family", "deployment_mode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_family: Mapped[str] = mapped_column(String(80), nullable=False)
    deployment_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class AIProvider(Base, TimestampMixin):
    __tablename__ = "ai_providers"
    __table_args__ = (Index("ix_ai_providers_family_mode", "provider_family", "deployment_mode"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    provider_name: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="configured")
    catalog_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    provider_family: Mapped[str | None] = mapped_column(String(80), nullable=True)
    deployment_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    display_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    encrypted_settings: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AIModelConfig(Base, TimestampMixin):
    __tablename__ = "ai_model_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    ai_provider_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("ai_providers.id"))
    model_name: Mapped[str] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class PromptDefinition(Base, TimestampMixin):
    """scope=platform: global defaults; scope=tenant: tenant override for the same ``prompt_key``."""

    __tablename__ = "prompt_definitions"
    __table_args__ = (Index("ix_prompt_definitions_scope_tenant_key", "scope", "tenant_id", "prompt_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    prompt_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)


class PromptVersion(Base, TimestampMixin):
    __tablename__ = "prompt_versions"
    __table_args__ = (Index("ix_prompt_versions_def_active", "prompt_definition_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_definition_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prompt_definitions.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    version_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PromptActivationEvent(Base):
    __tablename__ = "prompt_activation_events"
    __table_args__ = (Index("ix_prompt_activation_def", "prompt_definition_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_definition_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prompt_definitions.id", ondelete="CASCADE"), nullable=False
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    event_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TenantAiSettings(Base, TimestampMixin):
    __tablename__ = "tenant_ai_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    default_ai_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True
    )
    default_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fallback_ai_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True
    )
    fallback_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)


class TenantAiTaskRoute(Base, TimestampMixin):
    __tablename__ = "tenant_ai_task_routes"
    __table_args__ = (UniqueConstraint("tenant_id", "task_type", name="uq_tenant_ai_task_route"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    ai_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fallback_ai_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True
    )
    fallback_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_key: Mapped[str] = mapped_column(String(160), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AITaskRun(Base, TimestampMixin):
    __tablename__ = "ai_task_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    provider_family: Mapped[str | None] = mapped_column(String(80), nullable=True)
    deployment_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ai_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True
    )
    prompt_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prompt_definitions.id", ondelete="SET NULL"), nullable=True
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True, index=True
    )


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    details: Mapped[str | None] = mapped_column(Text)
