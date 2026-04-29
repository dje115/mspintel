from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Contact, Customer, Opportunity, Quote, SourceEntityMapping, SourceSystemConnection, Ticket
from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.capabilities import (
    CAP_CONTACTS,
    CAP_CUSTOMERS,
    CAP_OPPORTUNITIES,
    CAP_QUOTES,
    CAP_TICKETS,
)
from app.services.connectors.constants import (
    CONNECTOR_SYSTEM_AUTOTASK,
    ENTITY_CONTACT,
    ENTITY_CUSTOMER,
    ENTITY_OPPORTUNITY,
    ENTITY_QUOTE,
    ENTITY_TICKET,
)
from app.services.connectors.manifest import ConnectorConfigField, ConnectorManifest
from app.services.connectors.onboarding import ConnectorOnboardingService
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult
from app.services.connectors.utils import upsert_source_entity_mapping


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


class AutotaskConnectorAdapter(ConnectorAdapter):
    manifest = ConnectorManifest(
        key=CONNECTOR_SYSTEM_AUTOTASK,
        display_name="Autotask PSA",
        description="Read-only PSA ingestion for customers/contacts/tickets/opportunities/quotes.",
        system_family="psa",
        maturity="beta",
        auth_modes=("api_key",),
        capabilities=(CAP_CUSTOMERS, CAP_CONTACTS, CAP_TICKETS, CAP_OPPORTUNITIES, CAP_QUOTES),
        sync_modes=("manual", "delta"),
        connector_version="v1",
        default_cadence_minutes=30,
        implemented=True,
        import_scope_modes=("all", "selected_external_ids", "selected_names", "name_prefix", "sample_limit", "recent_active"),
        import_scope_filter_keys=("external_ids", "names", "name_prefix", "sample_limit", "recent_active_days"),
        config_fields=(
            ConnectorConfigField(key="base_url", label="Base URL", required=True, secret=False),
            ConnectorConfigField(key="api_key", label="API key", required=False, secret=True),
            ConnectorConfigField(key="token", label="Bearer token", required=False, secret=True),
            ConnectorConfigField(key="username", label="Username", required=False, secret=False),
            ConnectorConfigField(key="integration_code", label="Integration code", required=False, secret=False),
            ConnectorConfigField(key="secret", label="Secret", required=False, secret=True),
        ),
        ui_help_text=(
            "Requires Autotask REST API credentials (integration code, API user username, secret) and the tenant "
            "zone base URL. Recommended: resolve zone via /zoneInformation and use API-only user with tracking id."
        ),
    )

    def _customer_for_company(self, db: Session, tenant_id: UUID, connection_id: UUID, company_id: str) -> Customer | None:
        mapping = db.scalars(
            select(SourceEntityMapping).where(
                SourceEntityMapping.tenant_id == tenant_id,
                SourceEntityMapping.source_connection_id == connection_id,
                SourceEntityMapping.entity_type == ENTITY_CUSTOMER,
                SourceEntityMapping.source_id == company_id,
            )
        ).first()
        if mapping:
            return db.get(Customer, mapping.canonical_entity_id)
        return db.scalars(select(Customer).where(Customer.tenant_id == tenant_id, Customer.external_ref == company_id)).first()

    def _headers(self, config: dict) -> dict[str, str]:
        api_key = str(config.get("api_key") or "").strip()
        token = str(config.get("token") or "").strip()
        if api_key:
            return {"X-API-Key": api_key, "Content-Type": "application/json"}
        if token:
            return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        return {
            "ApiIntegrationcode": str(config.get("integration_code", "")),
            "UserName": str(config.get("username", "")),
            "Secret": str(config.get("secret", "")),
            "Content-Type": "application/json",
        }

    def validate_config(self, auth_mode: str, config: dict) -> list[str]:
        base_url = str(config.get("base_url") or "").strip()
        if not base_url:
            return ["base_url"]
        # Connector Lab and api-key mode
        if config.get("api_key") or config.get("token") or "/autotask" in base_url.rstrip("/"):
            return []
        missing = [k for k in ("integration_code", "username", "secret") if not config.get(k)]
        return missing

    @staticmethod
    def _is_connector_lab_mode(base_url: str, config: dict) -> bool:
        return bool(config.get("api_key") or config.get("token") or "/autotask" in base_url.rstrip("/"))

    def _base_url(self, connection: SourceSystemConnection, config: dict) -> str:
        base_url = (connection.base_url or config.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("Autotask base_url is required")
        return base_url

    def test_connection(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
    ) -> ConnectorTestResult:
        try:
            base_url = self._base_url(connection, config)
        except ValueError as exc:
            return ConnectorTestResult(ok=False, message=str(exc), checked_at=datetime.now(UTC))

        if self._is_connector_lab_mode(base_url, config):
            headers = self._headers(config)
            try:
                with httpx.Client(timeout=20.0) as client:
                    health = client.get(base_url.rsplit("/autotask", 1)[0] + "/health", headers=headers)
                    if health.status_code >= 500:
                        return ConnectorTestResult(
                            ok=False,
                            message=f"Base URL reachable but unhealthy (HTTP {health.status_code}).",
                            checked_at=datetime.now(UTC),
                        )
                    accounts = client.get(
                        f"{base_url}/accounts",
                        headers=headers,
                        params={"page": 1, "page_size": 1},
                    )
            except httpx.HTTPError:
                return ConnectorTestResult(
                    ok=False,
                    message="Unable to reach Autotask base URL. Check host/port and network routing.",
                    checked_at=datetime.now(UTC),
                )
            if accounts.status_code == 401:
                return ConnectorTestResult(
                    ok=False,
                    message="Autotask credentials were rejected by endpoint auth.",
                    checked_at=datetime.now(UTC),
                )
            if accounts.status_code == 404:
                return ConnectorTestResult(
                    ok=False,
                    message="Autotask namespace or accounts endpoint not found at configured base URL.",
                    checked_at=datetime.now(UTC),
                )
            if accounts.status_code >= 400:
                return ConnectorTestResult(
                    ok=False,
                    message=f"Autotask accounts endpoint failed with status {accounts.status_code}.",
                    checked_at=datetime.now(UTC),
                )
            payload = accounts.json() if accounts.content else {}
            if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                return ConnectorTestResult(
                    ok=False,
                    message="Autotask accounts endpoint returned unexpected payload shape.",
                    checked_at=datetime.now(UTC),
                )
            return ConnectorTestResult(
                ok=True,
                message="Autotask base URL, auth, namespace, and accounts endpoint checks passed.",
                checked_at=datetime.now(UTC),
                metadata={"checked_endpoint": "/autotask/accounts"},
            )

        required = ("integration_code", "username", "secret")
        missing = [k for k in required if not config.get(k)]
        if missing:
            return ConnectorTestResult(
                ok=False,
                message=f"Missing Autotask config keys: {', '.join(missing)}",
                checked_at=datetime.now(UTC),
            )
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(f"{base_url}/v1.0/Companies/query", headers=self._headers(config), params={"MaxRecords": 1})
                if resp.status_code >= 400:
                    return ConnectorTestResult(
                        ok=False,
                        message=f"Autotask test failed with status {resp.status_code}",
                        checked_at=datetime.now(UTC),
                    )
        except Exception:
            return ConnectorTestResult(
                ok=False,
                message="Unable to reach Autotask endpoint or credentials were rejected.",
                checked_at=datetime.now(UTC),
            )
        return ConnectorTestResult(
            ok=True,
            message="Connection succeeded.",
            checked_at=datetime.now(UTC),
            metadata={"checked_endpoint": "/v1.0/Companies/query"},
        )

    def _fetch_entities(self, base_url: str, headers: dict[str, str], path: str, since_cursor: str | None) -> list[dict]:
        is_lab = "/autotask/" in f"{base_url}/"
        query: dict[str, object] = {"page_size": 200} if is_lab else {"MaxRecords": 200}
        if since_cursor:
            query["updated_since" if is_lab else "Search"] = since_cursor if is_lab else f"LastActivityDate gt {since_cursor}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{base_url}{path}", headers=headers, params=query)
            if resp.status_code >= 400:
                raise ValueError(f"Autotask returned HTTP {resp.status_code} for {path}")
            payload = resp.json()
            if isinstance(payload, dict):
                if isinstance(payload.get("items"), list):
                    return payload["items"]
                if isinstance(payload.get("Items"), list):
                    return payload["Items"]
            return []

    def run_sync(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
        cursor: str | None,
    ) -> ConnectorSyncResult:
        base_url = self._base_url(connection, config)
        is_connector_lab = self._is_connector_lab_mode(base_url, config)
        accounts_path = "/accounts" if is_connector_lab else "/v1.0/Companies/query"
        contacts_path = "/contacts" if is_connector_lab else "/v1.0/Contacts/query"
        tickets_path = "/tickets" if is_connector_lab else "/v1.0/Tickets/query"
        opps_path = "/opportunities" if is_connector_lab else "/v1.0/Opportunities/query"
        quotes_path = "/quotes" if is_connector_lab else "/v1.0/Quotes/query"
        headers = self._headers(config)
        stats = ConnectorSyncStats()
        try:
            companies = self._fetch_entities(base_url, headers, accounts_path, cursor)
            scope_mode = connection.import_scope_mode or "all"
            scope_filters = connection.import_scope_filters or {}
            onboarding = ConnectorOnboardingService(db)
            tenant_customer_count = int(
                db.scalar(select(func.count()).where(Customer.tenant_id == tenant_id)) or 0
            )
            processed_companies = 0
            for company in companies:
                source_id = str(company.get("id") or company.get("idValue") or "")
                if not source_id:
                    continue
                name = str(company.get("companyName") or company.get("CompanyName") or f"Autotask Company {source_id}")
                if scope_mode == "selected_external_ids" and source_id not in set(scope_filters.get("external_ids") or []):
                    continue
                if scope_mode == "selected_names" and name not in set(scope_filters.get("names") or []):
                    continue
                if scope_mode == "name_prefix":
                    prefix = str(scope_filters.get("name_prefix") or "").lower()
                    if prefix and not name.lower().startswith(prefix):
                        continue
                if scope_mode == "sample_limit":
                    limit = int(scope_filters.get("sample_limit") or 0)
                    if limit > 0 and processed_companies >= limit:
                        break
                customer = self._customer_for_company(db, tenant_id, connection.id, source_id)
                if not customer:
                    candidate = onboarding.upsert_mapping_review_candidate(
                        tenant_id=tenant_id,
                        source_connection_id=connection.id,
                        entity_type=ENTITY_CUSTOMER,
                        source_external_id=source_id,
                        source_display_name=name,
                        source_domain=None,
                    )
                    if candidate.suggested_confidence == "high" and candidate.suggested_customer_id:
                        customer = db.get(Customer, candidate.suggested_customer_id)
                        if customer:
                            candidate.status = "accepted"
                            candidate.mapped_customer_id = customer.id
                if not customer and tenant_customer_count > 0:
                    stats.warnings.append(
                        f"Autotask account '{name}' requires mapping review before import."
                    )
                    continue
                if not customer:
                    customer = Customer(
                        tenant_id=tenant_id,
                        name=name,
                        status="active" if bool(company.get("isActive", True)) else "watch",
                        owner_name=company.get("ownerResourceName"),
                        external_ref=source_id,
                    )
                    db.add(customer)
                    db.flush()
                else:
                    customer.name = str(company.get("companyName") or customer.name)
                    customer.owner_name = company.get("ownerResourceName") or customer.owner_name
                    if "isActive" in company and not bool(company.get("isActive")):
                        customer.status = "watch"
                stats.customers_upserted += 1
                processed_companies += 1
                upsert_source_entity_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_CUSTOMER,
                    source_id=source_id,
                    canonical_entity_id=customer.id,
                )
                stats.mappings_written += 1

            # Queries below depend on account->customer mappings written in this run.
            db.flush()
            contacts = self._fetch_entities(base_url, headers, contacts_path, cursor)
            for src in contacts:
                source_id = str(src.get("id") or "")
                company_id = str(src.get("companyID") or src.get("companyId") or "")
                if not source_id or not company_id:
                    continue
                customer = self._customer_for_company(db, tenant_id, connection.id, company_id)
                if not customer:
                    stats.warnings.append(
                        f"Skipped contact {source_id}: account {company_id} is not mapped."
                    )
                    continue
                contact = db.scalars(
                    select(Contact).where(Contact.tenant_id == tenant_id, Contact.external_ref == source_id)
                ).first()
                name = f"{src.get('firstName') or ''} {src.get('lastName') or ''}".strip() or f"Contact {source_id}"
                if not contact:
                    contact = Contact(
                        tenant_id=tenant_id,
                        customer_id=customer.id,
                        name=name,
                        email=src.get("emailAddress"),
                        external_ref=source_id,
                    )
                    db.add(contact)
                else:
                    contact.customer_id = customer.id
                    contact.name = name
                    contact.email = src.get("emailAddress") or contact.email
                stats.contacts_upserted += 1
                db.flush()
                upsert_source_entity_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_CONTACT,
                    source_id=source_id,
                    canonical_entity_id=contact.id,
                )
                stats.mappings_written += 1

            tickets = self._fetch_entities(base_url, headers, tickets_path, cursor)
            for src in tickets:
                source_id = str(src.get("id") or "")
                company_id = str(src.get("companyID") or src.get("companyId") or "")
                if not source_id or not company_id:
                    continue
                customer = self._customer_for_company(db, tenant_id, connection.id, company_id)
                if not customer:
                    stats.warnings.append(
                        f"Skipped ticket {source_id}: account {company_id} is not mapped."
                    )
                    continue
                ticket = db.scalars(
                    select(Ticket).where(Ticket.tenant_id == tenant_id, Ticket.external_ref == source_id)
                ).first()
                t_status = str(src.get("status") or "open").lower()
                if not ticket:
                    ticket = Ticket(
                        tenant_id=tenant_id,
                        customer_id=customer.id,
                        status="open" if "complete" not in t_status and "closed" not in t_status else "closed",
                        subject=str(src.get("title") or src.get("description") or f"Ticket {source_id}"),
                        external_ref=source_id,
                    )
                    db.add(ticket)
                else:
                    ticket.customer_id = customer.id
                    ticket.status = "open" if "complete" not in t_status and "closed" not in t_status else "closed"
                    ticket.subject = str(src.get("title") or ticket.subject or f"Ticket {source_id}")
                stats.tickets_upserted += 1
                db.flush()
                upsert_source_entity_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_TICKET,
                    source_id=source_id,
                    canonical_entity_id=ticket.id,
                )
                stats.mappings_written += 1

            opportunities = self._fetch_entities(base_url, headers, opps_path, cursor)
            for src in opportunities:
                source_id = str(src.get("id") or "")
                company_id = str(src.get("companyID") or src.get("companyId") or "")
                if not source_id or not company_id:
                    continue
                customer = self._customer_for_company(db, tenant_id, connection.id, company_id)
                if not customer:
                    stats.warnings.append(
                        f"Skipped opportunity {source_id}: account {company_id} is not mapped."
                    )
                    continue
                opp = db.scalars(
                    select(Opportunity).where(Opportunity.tenant_id == tenant_id, Opportunity.external_ref == source_id)
                ).first()
                status = str(src.get("status") or "open").lower()
                value = src.get("amount")
                cents = int(float(value) * 100) if value is not None else None
                if not opp:
                    opp = Opportunity(
                        tenant_id=tenant_id,
                        customer_id=customer.id,
                        status="open" if status in {"new", "open", "active"} else status,
                        title=str(src.get("title") or f"Opportunity {source_id}"),
                        value_cents=cents,
                        external_ref=source_id,
                    )
                    db.add(opp)
                else:
                    opp.customer_id = customer.id
                    opp.status = "open" if status in {"new", "open", "active"} else status
                    opp.title = str(src.get("title") or opp.title or f"Opportunity {source_id}")
                    opp.value_cents = cents if cents is not None else opp.value_cents
                stats.opportunities_upserted += 1
                db.flush()
                upsert_source_entity_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_OPPORTUNITY,
                    source_id=source_id,
                    canonical_entity_id=opp.id,
                )
                stats.mappings_written += 1

            # v1 quote path: optional, only if endpoint responds
            try:
                quotes = self._fetch_entities(base_url, headers, quotes_path, cursor)
            except Exception:
                quotes = []
                stats.warnings.append("Quote endpoint not available; quote ingestion skipped.")
            for src in quotes:
                source_id = str(src.get("id") or "")
                company_id = str(src.get("companyID") or src.get("companyId") or "")
                if not source_id or not company_id:
                    continue
                customer = self._customer_for_company(db, tenant_id, connection.id, company_id)
                if not customer:
                    stats.warnings.append(
                        f"Skipped quote {source_id}: account {company_id} is not mapped."
                    )
                    continue
                quote = db.scalars(
                    select(Quote).where(Quote.tenant_id == tenant_id, Quote.external_ref == source_id)
                ).first()
                status = str(src.get("status") or "open").lower()
                value = src.get("totalAmount")
                cents = int(float(value) * 100) if value is not None else None
                if not quote:
                    quote = Quote(
                        tenant_id=tenant_id,
                        customer_id=customer.id,
                        status=status,
                        title=str(src.get("name") or f"Quote {source_id}"),
                        value_cents=cents,
                        source_system="autotask",
                        external_ref=source_id,
                    )
                    db.add(quote)
                else:
                    quote.customer_id = customer.id
                    quote.status = status
                    quote.title = str(src.get("name") or quote.title or f"Quote {source_id}")
                    quote.value_cents = cents if cents is not None else quote.value_cents
                stats.quotes_upserted += 1
                db.flush()
                upsert_source_entity_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_QUOTE,
                    source_id=source_id,
                    canonical_entity_id=quote.id,
                )
                stats.mappings_written += 1

        except Exception as exc:
            return ConnectorSyncResult(
                ok=False,
                message=str(exc),
                completed_at=datetime.now(UTC),
                next_cursor=cursor,
                stats=stats,
            )

        return ConnectorSyncResult(
            ok=True,
            message="Autotask sync completed.",
            completed_at=datetime.now(UTC),
            next_cursor=_iso_now(),
            stats=stats,
        )
