from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    Customer,
    FinanceBillingAccount,
    FinanceBillingSnapshot,
    FinanceInvoice,
    FinanceInvoiceLine,
    SourceEntityMapping,
    SourceSystemConnection,
)
from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.capabilities import CAP_BILLING_ACCOUNTS, CAP_INVOICES
from app.services.connectors.constants import (
    CONNECTOR_SYSTEM_XERO,
    ENTITY_CUSTOMER,
    ENTITY_FINANCE_BILLING_ACCOUNT,
    ENTITY_FINANCE_INVOICE,
)
from app.services.connectors.manifest import ConnectorConfigField, ConnectorManifest
from app.services.connectors.onboarding import ConnectorOnboardingService
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult
from app.services.connectors.utils import upsert_source_entity_mapping


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _to_cents(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return None


def _norm_name(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _parse_date(value: object) -> date | None:
    if not value:
        return None
    text = str(value)
    for candidate in (text, text.split("T", 1)[0]):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue
    return None


class XeroConnectorAdapter(ConnectorAdapter):
    """Thin Xero finance ingest for contacts + invoices + lines, Connector Lab compatible."""

    manifest = ConnectorManifest(
        key=CONNECTOR_SYSTEM_XERO,
        display_name="Xero (accounting)",
        description=(
            "Thin finance import: contacts + invoices + invoice lines with mapping-review-aware customer linkage. "
            "Supports Connector Lab for dev and generic Xero-like endpoints for live planning."
        ),
        system_family="accounting",
        maturity="experimental",
        auth_modes=("oauth2", "oauth", "api_key", "sandbox"),
        capabilities=(CAP_BILLING_ACCOUNTS, CAP_INVOICES),
        sync_modes=("manual", "delta"),
        connector_version="finance_v1",
        default_cadence_minutes=360,
        implemented=True,
        import_scope_modes=("all", "selected_external_ids", "selected_names", "sample_limit"),
        import_scope_filter_keys=("external_ids", "names", "sample_limit"),
        config_fields=(
            ConnectorConfigField(key="base_url", label="API base URL", required=False, secret=False),
            ConnectorConfigField(key="xero_tenant_id", label="Xero tenant ID", required=False, secret=False),
            ConnectorConfigField(key="access_token", label="Access token", required=False, secret=True),
            ConnectorConfigField(key="api_key", label="API key", required=False, secret=True),
            ConnectorConfigField(key="client_id", label="Client ID", required=False, secret=False),
            ConnectorConfigField(key="client_secret", label="Client Secret", required=False, secret=True),
            ConnectorConfigField(key="refresh_token", label="Refresh token", required=False, secret=True),
        ),
        ui_help_text=(
            "Xero requires OAuth2 + Xero-Tenant-Id. For Connector Lab development, use API key or bearer token "
            "with /xero contacts and invoices endpoints."
        ),
    )

    def _base_url(self, connection: SourceSystemConnection, config: dict) -> str:
        raw = (
            str(config.get("base_url") or "").strip()
            or str(connection.base_url or "").strip()
            or os.getenv("XERO_BASE_URL", "").strip()
            or os.getenv("CONNECTOR_LAB_BASE_URL", "").strip()
        )
        if not raw:
            raise ValueError("Missing Xero base URL. Set connection base_url/config.base_url or XERO_BASE_URL.")
        return raw.rstrip("/")

    @staticmethod
    def _tenant_header(config: dict) -> str | None:
        tid = (
            str(config.get("xero_tenant_id") or "").strip()
            or str(config.get("tenant_id") or "").strip()
            or os.getenv("XERO_TENANT_ID", "").strip()
        )
        return tid or None

    @staticmethod
    def _auth_headers(config: dict) -> dict[str, str]:
        headers: dict[str, str] = {}
        token = (
            str(config.get("access_token") or "").strip()
            or str(config.get("token") or "").strip()
            or os.getenv("XERO_ACCESS_TOKEN", "").strip()
        )
        api_key = str(config.get("api_key") or "").strip() or os.getenv("CONNECTOR_LAB_API_KEY", "").strip()
        lab_token = os.getenv("CONNECTOR_LAB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif lab_token:
            headers["Authorization"] = f"Bearer {lab_token}"
        if api_key:
            headers["X-API-Key"] = api_key
        return headers

    def _request_json(self, *, base_url: str, path: str, headers: dict[str, str], params: dict[str, str] | None = None) -> dict:
        url = f"{base_url}{path}"
        with httpx.Client(timeout=20.0) as client:
            res = client.get(url, headers=headers, params=params)
        if res.status_code == 401:
            raise ValueError("Xero auth failed (401). Check access token/API key.")
        if res.status_code == 400 and "xero-tenant-id" in res.text.lower():
            raise ValueError("Xero API requires Xero-Tenant-Id. Set xero_tenant_id in connector config.")
        if res.status_code >= 400:
            raise ValueError(f"Xero request failed for {path}: HTTP {res.status_code}.")
        payload = res.json()
        if not isinstance(payload, dict):
            raise ValueError(f"Unexpected payload from Xero endpoint {path}")
        return payload

    @staticmethod
    def _extract_items(payload: dict) -> list[dict]:
        rows = payload.get("items")
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []

    def _list_resource(self, *, base_url: str, path: str, headers: dict[str, str], since_cursor: str | None) -> list[dict]:
        page = 1
        rows: list[dict] = []
        while True:
            params: dict[str, str] = {"page": str(page), "page_size": "200"}
            if since_cursor:
                params["updated_since"] = since_cursor
            payload = self._request_json(base_url=base_url, path=path, headers=headers, params=params)
            items = self._extract_items(payload)
            rows.extend(items)
            has_more = bool(payload.get("has_more"))
            if not has_more or not items:
                break
            page += 1
        return rows

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
            headers = self._auth_headers(config)
            tenant_id_hdr = self._tenant_header(config)
            if tenant_id_hdr:
                headers["Xero-Tenant-Id"] = tenant_id_hdr
            with httpx.Client(timeout=15.0) as client:
                health = client.get(f"{base_url}/health", headers=headers)
                if health.status_code >= 500:
                    raise ValueError(f"Xero base URL unreachable ({health.status_code}).")
            # Contacts and invoices must be reachable for thin sync viability.
            self._request_json(base_url=base_url, path="/xero/contacts", headers=headers, params={"page": "1", "page_size": "1"})
            self._request_json(base_url=base_url, path="/xero/invoices", headers=headers, params={"page": "1", "page_size": "1"})
            return ConnectorTestResult(
                ok=True,
                message="Xero connectivity checks passed: base URL, auth, tenant header, contacts, invoices.",
                checked_at=datetime.now(UTC),
                metadata={"base_url": base_url, "mode": "xero_thin_v1"},
            )
        except ValueError as exc:
            return ConnectorTestResult(ok=False, message=str(exc), checked_at=datetime.now(UTC))

    def _customer_from_mapping(self, db: Session, tenant_id: UUID, connection_id: UUID, source_contact_id: str) -> Customer | None:
        mapped_customer_id = db.scalar(
            select(SourceEntityMapping.canonical_entity_id).where(
                SourceEntityMapping.tenant_id == tenant_id,
                SourceEntityMapping.source_connection_id == connection_id,
                SourceEntityMapping.entity_type == ENTITY_CUSTOMER,
                SourceEntityMapping.source_id == source_contact_id,
            )
        )
        if not mapped_customer_id:
            return None
        return db.get(Customer, mapped_customer_id)

    def _upsert_billing_account(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection_id: UUID,
        contact: dict,
        customer: Customer | None,
    ) -> FinanceBillingAccount:
        contact_id = str(contact.get("ContactID") or contact.get("id") or "").strip()
        name = str(contact.get("Name") or contact.get("name") or f"Xero Contact {contact_id}").strip()
        currency = str(contact.get("DefaultCurrency") or contact.get("currency") or "GBP")
        row = db.scalars(
            select(FinanceBillingAccount).where(
                FinanceBillingAccount.tenant_id == tenant_id,
                FinanceBillingAccount.source_connection_id == connection_id,
                FinanceBillingAccount.external_billing_account_id == contact_id,
            )
        ).first()
        linkage = "linked" if customer else "unlinked"
        notes = None if customer else "No canonical customer mapping yet; resolve in Mapping review to unlock account-level finance context."
        payload_extra = {
            "source": "xero",
            "contact_name": name,
            "contact_id": contact_id,
            "source_domain": contact.get("EmailAddress") or contact.get("emailAddress"),
        }
        if not row:
            row = FinanceBillingAccount(
                tenant_id=tenant_id,
                customer_id=customer.id if customer else None,
                source_connection_id=connection_id,
                external_billing_account_id=contact_id,
                display_name=name[:220],
                currency_code=currency[:12],
                linkage_status=linkage,
                coverage_notes=notes,
                extra=payload_extra,
            )
            db.add(row)
        else:
            row.customer_id = customer.id if customer else row.customer_id
            row.display_name = name[:220]
            row.currency_code = currency[:12]
            row.linkage_status = linkage if customer else row.linkage_status
            row.coverage_notes = None if customer else row.coverage_notes
            row.extra = payload_extra
        db.flush()
        return row

    def _upsert_invoice(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection_id: UUID,
        account: FinanceBillingAccount,
        invoice: dict,
    ) -> FinanceInvoice:
        invoice_ext_id = str(invoice.get("InvoiceID") or invoice.get("id") or "").strip()
        status = str(invoice.get("Status") or invoice.get("status") or "unknown")
        total_cents = _to_cents(invoice.get("Total") or invoice.get("total")) or 0
        amount_due_cents = _to_cents(invoice.get("AmountDue") or invoice.get("amount_due"))
        amount_paid_cents = _to_cents(invoice.get("AmountPaid") or invoice.get("amount_paid"))
        outstanding = amount_due_cents if amount_due_cents is not None else max(total_cents - (amount_paid_cents or 0), 0)
        due_date = _parse_date(invoice.get("DueDate") or invoice.get("due_date"))
        issue_date = _parse_date(invoice.get("Date") or invoice.get("date") or invoice.get("issue_date"))
        invoice_no = str(invoice.get("InvoiceNumber") or invoice.get("invoice_number") or "").strip() or None
        row = db.scalars(
            select(FinanceInvoice).where(
                FinanceInvoice.tenant_id == tenant_id,
                FinanceInvoice.billing_account_id == account.id,
                FinanceInvoice.external_invoice_id == invoice_ext_id,
            )
        ).first()
        extra = {
            "source": "xero",
            "invoice_number": invoice_no,
            "amount_paid_cents": amount_paid_cents,
            "raw_status": status,
        }
        if not row:
            row = FinanceInvoice(
                tenant_id=tenant_id,
                billing_account_id=account.id,
                source_connection_id=connection_id,
                external_invoice_id=invoice_ext_id,
                status=status[:40],
                total_cents=total_cents,
                outstanding_cents=outstanding,
                currency_code=(invoice.get("CurrencyCode") or account.currency_code or "GBP")[:12],
                issue_date=issue_date,
                due_date=due_date,
                extra=extra,
            )
            db.add(row)
        else:
            row.status = status[:40]
            row.total_cents = total_cents
            row.outstanding_cents = outstanding
            row.currency_code = (invoice.get("CurrencyCode") or row.currency_code or account.currency_code or "GBP")[:12]
            row.issue_date = issue_date
            row.due_date = due_date
            row.extra = extra
        db.flush()
        return row

    def _upsert_invoice_line(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection_id: UUID,
        invoice_row: FinanceInvoice,
        line: dict,
    ) -> None:
        external_line_id = str(line.get("id") or line.get("LineItemID") or "").strip()
        if not external_line_id:
            external_line_id = _norm_name(
                f"{line.get('description')}-{line.get('qty')}-{line.get('unit_amount')}-{line.get('tax_amount')}"
            )[:120]
        quantity_raw = line.get("quantity") if line.get("quantity") is not None else line.get("qty")
        quantity = Decimal(str(quantity_raw)) if quantity_raw is not None else None
        unit_amount = _to_cents(line.get("unit_amount") or line.get("UnitAmount"))
        tax_amount = _to_cents(line.get("tax_amount") or line.get("TaxAmount"))
        line_total = _to_cents(line.get("line_total") or line.get("LineAmount"))
        row = db.scalars(
            select(FinanceInvoiceLine).where(
                FinanceInvoiceLine.tenant_id == tenant_id,
                FinanceInvoiceLine.invoice_id == invoice_row.id,
                FinanceInvoiceLine.external_line_id == external_line_id,
            )
        ).first()
        payload_extra = {"source": "xero"}
        if not row:
            row = FinanceInvoiceLine(
                tenant_id=tenant_id,
                invoice_id=invoice_row.id,
                source_connection_id=connection_id,
                external_line_id=external_line_id,
                description=str(line.get("description") or line.get("Description") or "")[:500] or None,
                quantity=quantity,
                unit_amount_cents=unit_amount,
                line_total_cents=line_total,
                tax_amount_cents=tax_amount,
                account_code=str(line.get("account_code") or line.get("AccountCode") or "")[:80] or None,
                extra=payload_extra,
            )
            db.add(row)
        else:
            row.description = str(line.get("description") or line.get("Description") or "")[:500] or row.description
            row.quantity = quantity
            row.unit_amount_cents = unit_amount
            row.line_total_cents = line_total
            row.tax_amount_cents = tax_amount
            row.account_code = str(line.get("account_code") or line.get("AccountCode") or "")[:80] or row.account_code
            row.extra = payload_extra

    def _upsert_snapshot_for_account(self, *, db: Session, tenant_id: UUID, account: FinanceBillingAccount) -> None:
        totals = db.execute(
            select(
                func.count(FinanceInvoice.id),
                func.sum(FinanceInvoice.outstanding_cents),
                func.sum(FinanceInvoice.total_cents),
            ).where(FinanceInvoice.tenant_id == tenant_id, FinanceInvoice.billing_account_id == account.id)
        ).first()
        invoice_count = int(totals[0] or 0)
        outstanding = int(totals[1] or 0)
        total = int(totals[2] or 0)
        status_summary = "none"
        if outstanding > 0:
            status_summary = "invoice_due"
        snap = db.scalars(
            select(FinanceBillingSnapshot).where(
                FinanceBillingSnapshot.tenant_id == tenant_id,
                FinanceBillingSnapshot.billing_account_id == account.id,
                FinanceBillingSnapshot.effective_date == date.today(),
            )
        ).first()
        payload = dict(
            tenant_id=tenant_id,
            billing_account_id=account.id,
            source_connection_id=account.source_connection_id,
            effective_date=date.today(),
            payment_status_summary=status_summary,
            aged_outstanding_cents=outstanding,
            confidence_level="medium" if account.customer_id else "low",
            coverage_notes=(
                "Xero invoices synced. Revenue assurance checks still need service/contract telemetry for full variance analysis."
            ),
            extra={"invoice_count": invoice_count, "total_cents": total},
        )
        if snap:
            for key, value in payload.items():
                setattr(snap, key, value)
        else:
            db.add(FinanceBillingSnapshot(**payload))

    def run_sync(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
        cursor: str | None,
    ) -> ConnectorSyncResult:
        stats = ConnectorSyncStats()
        now = datetime.now(UTC)
        try:
            base_url = self._base_url(connection, config)
            headers = self._auth_headers(config)
            tenant_hdr = self._tenant_header(config)
            if tenant_hdr:
                headers["Xero-Tenant-Id"] = tenant_hdr

            contacts = self._list_resource(base_url=base_url, path="/xero/contacts", headers=headers, since_cursor=cursor)
            invoices = self._list_resource(base_url=base_url, path="/xero/invoices", headers=headers, since_cursor=cursor)
            lines = self._list_resource(base_url=base_url, path="/xero/invoice-lines", headers=headers, since_cursor=cursor)

            scope_mode = connection.import_scope_mode or "all"
            scope_filters = connection.import_scope_filters or {}
            selected_external_ids = {str(v) for v in (scope_filters.get("external_ids") or [])}
            selected_names = {str(v) for v in (scope_filters.get("names") or [])}
            sample_limit = int(scope_filters.get("sample_limit") or 0)

            onboarding = ConnectorOnboardingService(db)
            by_contact_id: dict[str, FinanceBillingAccount] = {}
            processed = 0
            for contact in contacts:
                source_contact_id = str(contact.get("ContactID") or contact.get("id") or "").strip()
                if not source_contact_id:
                    continue
                source_name = str(contact.get("Name") or contact.get("name") or "").strip() or source_contact_id
                if scope_mode == "selected_external_ids" and source_contact_id not in selected_external_ids:
                    continue
                if scope_mode == "selected_names" and source_name not in selected_names:
                    continue
                if scope_mode == "sample_limit" and sample_limit > 0 and processed >= sample_limit:
                    break

                source_domain = None
                email = str(contact.get("EmailAddress") or contact.get("emailAddress") or "").strip().lower()
                if "@" in email:
                    source_domain = email.rsplit("@", 1)[1]

                customer = self._customer_from_mapping(db, tenant_id, connection.id, source_contact_id)
                if not customer:
                    review = onboarding.upsert_mapping_review_candidate(
                        tenant_id=tenant_id,
                        source_connection_id=connection.id,
                        entity_type=ENTITY_CUSTOMER,
                        source_external_id=source_contact_id,
                        source_display_name=source_name,
                        source_domain=source_domain,
                    )
                    if review.suggested_confidence == "high" and review.suggested_customer_id:
                        suggested = db.get(Customer, review.suggested_customer_id)
                        if suggested and suggested.tenant_id == tenant_id:
                            customer = suggested
                            review.status = "accepted"
                            review.mapped_customer_id = suggested.id
                            upsert_source_entity_mapping(
                                db=db,
                                tenant_id=tenant_id,
                                source_connection_id=connection.id,
                                entity_type=ENTITY_CUSTOMER,
                                source_id=source_contact_id,
                                canonical_entity_id=suggested.id,
                            )
                            stats.mappings_written += 1

                acct = self._upsert_billing_account(
                    db=db,
                    tenant_id=tenant_id,
                    connection_id=connection.id,
                    contact=contact,
                    customer=customer,
                )
                stats.finance_billing_accounts_upserted += 1
                processed += 1
                by_contact_id[source_contact_id] = acct
                upsert_source_entity_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_FINANCE_BILLING_ACCOUNT,
                    source_id=source_contact_id,
                    canonical_entity_id=acct.id,
                )
                stats.mappings_written += 1

            by_invoice_local_id: dict[str, FinanceInvoice] = {}
            for inv in invoices:
                local_invoice_id = str(inv.get("id") or "").strip()
                contact_ref = inv.get("Contact") or {}
                source_contact_id = str(contact_ref.get("ContactID") or inv.get("contact_id") or "").strip()
                if not source_contact_id:
                    stats.warnings.append("Skipped Xero invoice with missing contact reference.")
                    continue
                account = by_contact_id.get(source_contact_id)
                if not account:
                    # If contact row wasn't in this page/filter, recover account from canonical mapping.
                    account = db.scalars(
                        select(FinanceBillingAccount).where(
                            FinanceBillingAccount.tenant_id == tenant_id,
                            FinanceBillingAccount.source_connection_id == connection.id,
                            FinanceBillingAccount.external_billing_account_id == source_contact_id,
                        )
                    ).first()
                if not account:
                    stats.warnings.append(f"Skipped invoice for unlinked contact {source_contact_id}.")
                    continue
                inv_row = self._upsert_invoice(
                    db=db,
                    tenant_id=tenant_id,
                    connection_id=connection.id,
                    account=account,
                    invoice=inv,
                )
                stats.finance_invoices_upserted += 1
                if local_invoice_id:
                    by_invoice_local_id[local_invoice_id] = inv_row
                upsert_source_entity_mapping(
                    db=db,
                    tenant_id=tenant_id,
                    source_connection_id=connection.id,
                    entity_type=ENTITY_FINANCE_INVOICE,
                    source_id=inv_row.external_invoice_id,
                    canonical_entity_id=inv_row.id,
                )
                stats.mappings_written += 1

            for line in lines:
                invoice_local_id = str(line.get("invoice_id") or line.get("InvoiceID") or "").strip()
                inv_row = by_invoice_local_id.get(invoice_local_id)
                if not inv_row:
                    continue
                self._upsert_invoice_line(
                    db=db,
                    tenant_id=tenant_id,
                    connection_id=connection.id,
                    invoice_row=inv_row,
                    line=line,
                )

            # Refresh daily account snapshots from invoices.
            account_ids = [a.id for a in by_contact_id.values()]
            if account_ids:
                for account_id in account_ids:
                    account = db.get(FinanceBillingAccount, account_id)
                    if account:
                        self._upsert_snapshot_for_account(db=db, tenant_id=tenant_id, account=account)
                        stats.finance_snapshots_upserted += 1

            stats.warnings.append(
                "Xero thin import provides finance-side signals only; revenue assurance conclusions still require service/contract telemetry."
            )
            return ConnectorSyncResult(
                ok=True,
                message=(
                    f"Xero sync completed: contacts={stats.finance_billing_accounts_upserted}, "
                    f"invoices={stats.finance_invoices_upserted}."
                ),
                completed_at=now,
                next_cursor=_iso_now(),
                stats=stats,
            )
        except ValueError as exc:
            return ConnectorSyncResult(
                ok=False,
                message=str(exc),
                completed_at=now,
                next_cursor=cursor,
                stats=stats,
            )
