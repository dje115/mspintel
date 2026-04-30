"""Demo tenant structural seed helpers.

This module intentionally avoids seeding synthetic business telemetry
(customers, tickets, quotes, finance facts, posture facts). It keeps only:
- cleanup of prior demo business rows
- connector connection bootstrap aimed at Connector Lab
"""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.ai_settings_crypto import encrypt_settings_payload
from app.models.entities import (
    AccountScore,
    Action,
    AITaskRun,
    ConnectorMappingReview,
    Contact,
    Customer,
    FinanceBillingAccount,
    FinanceBillingSnapshot,
    FinanceInvoice,
    IntegrationSyncRun,
    M365CustomerPosture,
    Opportunity,
    Quote,
    Recommendation,
    SourceEntityMapping,
    SourceSystemConnection,
    Tenant,
    Ticket,
)

DEMO_TENANT_SLUG = "demo-msp"


def _clear_tenant_business_data(db: Session, tenant_id: UUID) -> None:
    """Remove connector-backed telemetry for demo tenant reseeds."""
    db.execute(delete(AITaskRun).where(AITaskRun.tenant_id == tenant_id))
    db.execute(delete(Recommendation).where(Recommendation.tenant_id == tenant_id))
    db.execute(delete(Action).where(Action.tenant_id == tenant_id))
    db.execute(delete(AccountScore).where(AccountScore.tenant_id == tenant_id))
    db.execute(delete(Ticket).where(Ticket.tenant_id == tenant_id))
    db.execute(delete(Opportunity).where(Opportunity.tenant_id == tenant_id))
    db.execute(delete(Quote).where(Quote.tenant_id == tenant_id))
    db.execute(delete(Contact).where(Contact.tenant_id == tenant_id))
    db.execute(delete(ConnectorMappingReview).where(ConnectorMappingReview.tenant_id == tenant_id))
    db.execute(delete(SourceEntityMapping).where(SourceEntityMapping.tenant_id == tenant_id))
    db.execute(delete(IntegrationSyncRun).where(IntegrationSyncRun.tenant_id == tenant_id))
    db.execute(delete(M365CustomerPosture).where(M365CustomerPosture.tenant_id == tenant_id))
    db.execute(delete(FinanceBillingSnapshot).where(FinanceBillingSnapshot.tenant_id == tenant_id))
    db.execute(delete(FinanceInvoice).where(FinanceInvoice.tenant_id == tenant_id))
    db.execute(delete(FinanceBillingAccount).where(FinanceBillingAccount.tenant_id == tenant_id))
    db.execute(delete(Customer).where(Customer.tenant_id == tenant_id))
    db.execute(delete(SourceSystemConnection).where(SourceSystemConnection.tenant_id == tenant_id))
    db.flush()


def _seed_demo_connector_connections(db: Session, tenant_id: UUID) -> None:
    """Create demo connector connection rows targeting Connector Lab."""
    specs = [
        {
            "system_type": "autotask",
            "display_name": "Autotask PSA (Connector Lab)",
            "base_url": "http://connector-lab:8099/autotask",
            "auth_mode": "api_key",
            "config": {"api_key": "connector-lab-api-key"},
        },
        {
            "system_type": "itquoter",
            "display_name": "ITQuoter (Connector Lab)",
            "base_url": "http://connector-lab:8099/itquoter",
            "auth_mode": "api_key",
            "config": {"api_key": "connector-lab-api-key"},
        },
        {
            "system_type": "xero",
            "display_name": "Xero (Connector Lab)",
            "base_url": "http://connector-lab:8099",
            "auth_mode": "oauth",
            "config": {
                "token": "connector-lab-dev-token",
                "tenant_id": "demo-tenant-id",
                "xero_tenant_id": "demo-tenant-id",
            },
        },
        {
            "system_type": "microsoft_365",
            "display_name": "Microsoft 365 (Connector Lab)",
            "base_url": "http://connector-lab:8099",
            "auth_mode": "oauth2",
            "config": {
                "tenant_id": "demo-msp",
                "client_id": "connector-lab-demo-client",
                "client_secret": "connector-lab-demo-secret",
                "token": "connector-lab-dev-token",
            },
        },
        {
            "system_type": "veeam",
            "display_name": "Veeam (Connector Lab)",
            "base_url": "http://connector-lab:8099/veeam",
            "auth_mode": "api_key",
            "config": {"api_key": "connector-lab-api-key"},
        },
        {
            "system_type": "3cx",
            "display_name": "3CX (Connector Lab)",
            "base_url": "http://connector-lab:8099/3cx",
            "auth_mode": "api_key",
            "config": {"api_key": "connector-lab-api-key"},
        },
    ]
    for spec in specs:
        db.add(
            SourceSystemConnection(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                system_type=spec["system_type"],
                provider_family="generic",
                display_name=spec["display_name"],
                base_url=spec["base_url"],
                auth_mode=spec["auth_mode"],
                encrypted_config=encrypt_settings_payload(spec["config"]),
                status="configured",
                health_status="unknown",
                test_status=None,
                test_message=None,
                is_enabled=True,
                sync_cadence_minutes=60,
                lifecycle_state="configured",
                sync_behavior="manual_sync_only",
                import_scope_mode="all",
            )
        )
    db.flush()


def replace_demo_tenant_workspace(db: Session, tenant_id: UUID) -> int:
    """Reset demo tenant to structural/config baseline and connector bootstrap only."""
    _clear_tenant_business_data(db, tenant_id)
    _seed_demo_connector_connections(db, tenant_id)
    return 0


def seed_demo_workspace_if_demo_tenant(db: Session, tenant: Tenant | None) -> int:
    """If tenant is the demo MSP slug, reset to structural-only workspace state."""
    if tenant is None or tenant.slug != DEMO_TENANT_SLUG:
        return 0
    return replace_demo_tenant_workspace(db, tenant.id)

