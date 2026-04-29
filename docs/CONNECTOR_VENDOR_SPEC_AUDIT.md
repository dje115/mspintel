# Connector Vendor Spec Audit (thin slice)

Last updated: 2026-04-29  
Scope: connector realism audit for Autotask, ITQuoter, Xero, Microsoft Graph, Veeam, and 3CX; align manifests, Connector Lab, and product docs.

## Guardrails

- This audit is documentation/spec/emulator alignment only; no live customer API calls.
- Sources below prioritize official vendor docs; where public detail is incomplete or login-gated, caveats are called out.
- Connector maturity remains honest (`planned` / `stub` / `experimental` / `beta`) and does not imply production readiness.

## Source Links (official/reference)

- Autotask REST:
  - https://autotask.net/help/developerhelp/Content/APIs/REST/API_Calls/REST_ZoneInformation.htm
  - https://ww1.autotask.net/help/DeveloperHelp/Content/APIs/REST/General_Topics/REST_Security_Auth.htm
  - https://autotask.net/help/developerhelp/Content/APIs/General/ThreadLimiting.htm
  - https://autotask.net/help/developerhelp/content/apis/Webhooks/REST_WebhooksEntity.htm
- ITQuoter / Quoter public references:
  - https://itquoter.com/faq.html
  - https://docs.quoter.com/api
- Xero:
  - https://developer.xero.com/documentation/guides/oauth2/tenants/
  - https://developer.xero.com/documentation/api/accounting/contacts
  - https://developer.xero.com/documentation/api/accounting/invoices
  - https://developer.xero.com/documentation/api/accounting/payments
  - https://developer.xero.com/documentation/api/accounting/creditnotes
  - https://developer.xero.com/documentation/best-practices/api-call-efficiencies/if-modified-since/
- Microsoft Graph:
  - https://learn.microsoft.com/en-us/graph/api/organization-get?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/resources/organization?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/user-list?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/paging
  - https://learn.microsoft.com/en-us/graph/api/resources/subscribedsku?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/subscribedsku-list?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/resources/licensedetails?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/user-list-licensedetails?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/reportroot-getoffice365activeuserdetail?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/delta-query-users?tabs=http
  - https://learn.microsoft.com/en-us/graph/throttling
  - https://learn.microsoft.com/en-us/graph/api/adminreportsettings-update?view=graph-rest-1.0
- Veeam Service Provider Console (VSPC):
  - https://helpcenter.veeam.com/docs/vac/rest/oauth.html?ver=81
  - https://helpcenter.veeam.com/docs/vac/rest/api_keys.html?ver=81
  - https://helpcenter.veeam.com/references/vac/9.1/rest/3.6.1/tag/Companies/index.html
  - https://helpcenter.veeam.com/references/vac/9.1/rest/3.6.1/tag/Backup-Server-Jobs/index.html
- 3CX:
  - https://3cx.com/docs/cdr-call-data-records
  - https://3cx.com/docs/call-detail-record-guide

## Vendor-by-vendor audit

### 1) Autotask PSA REST API

- **Auth model:** API integration code + API user username + secret; API-only user security profile required.
- **Base URL / zone:** determine via `zoneInformation` before regular calls; use zone-specific `/atservicesrest/v1.0`.
- **Key entities for MSPIntel:** Companies, Contacts, Tickets, Opportunities, Quotes, Contracts (+ optionally Ticket Notes/Activities).
- **Pagination/query:** `/Entity/query`, `MaxRecords` (1-500), advanced query filters, count endpoint.
- **Delta strategy:** filter on activity/update timestamps; webhook support for selected entities.
- **Rate/supportability:** call threshold and per-endpoint thread-limiting guidance apply; plan retries/backoff.
- **Metadata:** `entityInformation` / `entityInformation/fields` for capability discovery, UDF awareness, webhook support flags.
- **Current Connector Lab emulation:** accounts/contacts/tickets/opportunities/quotes with updated timestamps and mismatched identity cases.
- **Gap vs real API:** connector-lab uses simplified path names and envelope (`items`) rather than full Autotask resource/query semantics.

### 2) ITQuoter

- **Auth model:** public ITQuoter FAQ states OAuth2; public Quoter docs expose OAuth2 client-credential style flows (vendor naming differs in public docs).
- **Base/API family:** REST API with quote-centric resources.
- **Key entities for MSPIntel:** customers/accounts, quotes, quote lines, quote statuses/stages, SKU/manufacturer hints where available.
- **Delta/pagination:** vendor docs indicate REST pagination; explicit incremental strategy should be connector-implemented (updated timestamps/modified windows).
- **Known caveat:** official ITQuoter developer docs are not fully open/publicly detailed in one canonical source; treat public references as directional and validate with sandbox onboarding.
- **Current Connector Lab emulation:** customers, quotes, quote lines, quote statuses with lost/stalled scenarios.
- **Gap vs real API:** no authenticated vendor-specific response envelope or webhook emulation yet.

### 3) Xero Accounting API

- **Auth model:** OAuth2; tenant discovery via `GET /connections`.
- **Tenant scoping:** include `Xero-Tenant-Id` header for Accounting API calls.
- **Key entities for MSPIntel:** Contacts, Invoices, Invoice line items, Payments, CreditNotes (for payment friction and billing integrity).
- **Delta/pagination:** `If-Modified-Since` header on relevant endpoints; page/pageSize supported on major accounting endpoints.
- **Identity keys:** `ContactID`, `InvoiceID` are canonical stable IDs; names are useful but non-authoritative for mapping.
- **Current Connector Lab emulation:** contacts/invoices/invoice-lines/payment-statuses plus aged debt scenarios.
- **Gap vs real API:** simplified payload shape, no native Xero top-level object wrappers.

### 4) Microsoft 365 / Microsoft Graph

- **Auth model:** Microsoft Entra OAuth2 with admin consent for app scopes.
- **Key APIs:** `/organization`, `/users`, `/subscribedSkus`, `/users/{id}/licenseDetails`, usage reports endpoints, user delta endpoints.
- **Permissions/scopes (typical read path):** `Organization.Read.All`, `User.Read.All`, `Directory.Read.All`, `Reports.Read.All`.
- **Mailbox/shared mailbox note:** Graph can provide user/mailbox signals and usage reports; shared-mailbox admin operations remain Exchange-admin-centric and may require non-Graph paths.
- **Privacy caveat:** usage reports may conceal names (`displayConcealedNames`) depending on tenant report settings.
- **Delta/pagination:** `@odata.nextLink` pagination and delta tokens for incremental user sync.
- **Throttling:** HTTP 429 with `Retry-After`; backoff policy required.
- **Current Connector Lab emulation:** Graph-inspired `/m365/organization`, `/m365/users`, `/m365/subscribedSkus`, `/m365/users/{id}/licenseDetails`, plus convenience/reporting endpoints (`/m365/licence-summary`, `/m365/mailbox-counts`, `/m365/hygiene-findings`) and a dev-only metadata endpoint (`/m365/lab-scenarios`).
- **Payload realism rule:** normal `/m365/*` vendor-shaped responses must not include MSPIntel control fields (`auto_confirm_customer`, `customer_hint`, or `mspintel_*`). Mapping-control metadata lives only in dev-only scenario endpoints.
- **Gap vs real API:** emulator uses practical `page/page_size` alongside Graph-style `value` / `@odata.nextLink`; it is not a complete permissions/scope or delta-token clone.

### Microsoft Graph caveats used in this slice

- `GET /users` is modeled with `value` plus `@odata.nextLink`; Graph paging guidance expects callers to follow the returned URL directly.
- `subscribedSkus` and `licenseDetails` include only fields needed by MSPIntel mapping/posture flows (`skuId`, `skuPartNumber`, `servicePlans`, `prepaidUnits`, `consumedUnits`).
- Throttling realism remains lightweight: Connector Lab can force HTTP 429 for failure-path testing, while retry policy guidance follows Graph `Retry-After` + exponential-backoff recommendations.

### 5) Veeam (VSPC-first recommendation)

- **Recommended first API family:** Veeam Service Provider Console REST API v3 for MSP multi-company visibility.
- **Auth model:** token endpoint (`POST /api/v3/token` password/refresh flow), optional API-key model in newer docs.
- **Key entities for MSPIntel:** organizations/companies, backup jobs, workloads/resources, repositories/storage, restore-test evidence, usage/licensing surfaces where available.
- **Delta/pagination:** offset/limit style query parameters.
- **Versioning:** VSPC API versioned by `/api/v3`; older VAC docs exist and differ by version.
- **Current Connector Lab emulation:** customers, backup jobs, workloads, repositories, restore tests.
- **Gap vs real API:** no true VSPC path taxonomy or token issuance flow emulated yet.

### 6) 3CX (optional/later)

- **Recommended first ingestion path:** CDR export/feed (file/socket) as practical first slice.
- **Key entities for MSPIntel:** call records (inbound/outbound, duration, answer/termination), extensions/agents, queue-oriented context where available.
- **Limitations:** API depth and access model differ by 3CX version/deployment; CDR format and storage paths are operationally configurable.
- **Current Connector Lab emulation:** calls + extensions.
- **Gap vs real path:** no CDR stream/socket behavior and no queue-level topology emulation.

## Connector Lab realism updates in this slice

- Added more vendor-like payload fields in `tools/connector_lab/app/data.py`:
  - Autotask-like: `companyName`, `companyID`, `emailAddress`, `title`, `totalAmount`, etc.
  - Xero-like: `ContactID`, `InvoiceID`, `AmountDue`, nested `Contact`.
  - Graph-like: `displayName`, `userPrincipalName`, `accountEnabled`.
  - Veeam-like: `instanceUid`.
- Added `has_more` to list payloads in `tools/connector_lab/app/main.py` for clearer pagination semantics.
- Added Xero realism guard: `Xero-Tenant-Id` header now required for `/xero/*` endpoints.
- Expanded Connector Lab datasets to include ~20+ additional customer/account-level scenarios per vendor namespace, with deliberately messy identity and signal cases (match/no-match, legal-name variants, stalled/lost quotes, aged invoices, M365 hygiene mismatches, failed/stale backups, restore-test gaps).
- Customer naming now uses realistic UK-style organisations across namespaces; generic `ConnectorLab Scenario Customer XX` labels are removed from normal payloads.
- M365 sync behavior should emit mapping-review states (`accepted`, `pending`, `unlinked`) so uncertain identity links remain visible in `/app/integrations/mappings`.
- Autotask adapter now supports Connector Lab auth/namespace/account-endpoint checks in `test_connection` and keeps vendor-style credential checks available for real API mode.
- Autotask sync now avoids silent duplicate customer creation when canonical baseline customers already exist; unmatched accounts are sent to mapping review and downstream entities are skipped with explicit sync warnings.

## Manifest/catalog alignment updates in this slice

- Updated connector metadata/help text to better match vendor auth/scope reality:
  - Autotask: zone discovery + API-only user/tracking guidance.
  - Xero: OAuth2 + tenant header + scope expectations.
  - Microsoft 365: planned Graph read scopes clarified.
- Updated planned/stub auth-mode metadata:
  - ITQuoter: now advertises `oauth2` and `api_key` (still stub).
  - Veeam: now includes `api_key` alongside token/user-password patterns.
  - 3CX: shifted to `api_key`/`none` to reflect CDR-export-first path.

## Canonical-model fit assessment (no large schema changes in this slice)

| Canonical need | Current fit | Notes |
|---|---|---|
| Customers/accounts | Partial-good | Customer model + mapping review already usable; stronger external-identity strategy still needed per connector. |
| Contacts/stakeholders | Partial-good | Canonical contacts exist; role richness and relationship metadata still shallow. |
| Tickets/service pressure | Good for thin slice | Ticket model supports pressure signals; deeper SLA fields still future. |
| Opportunities/quotes | Partial-good | Current entities support core lifecycle; quote-line detail remains sparse. |
| Invoices/invoice lines | Partial-good | Finance phase introduced canonical invoice layer; live Xero path still limited. |
| M365 posture | Good for practical v1.5 | Canonical posture exists; live Graph depth still intentionally constrained. |
| Backup posture | Partial | Placeholder + future Veeam canonical depth needed. |
| Mapping review | Good thin slice | Review queue/actions/audit flow implemented; matcher quality can improve. |
| Confidence notes | Partial-good | Present in multiple surfaces; still needs broader consistency in future slices. |
| Risk engine inputs | Partial-good | Works on existing signals; richer connector depth will improve quality. |
| Billing integrity | Partial-good | Canonical finance exists; live reconciliation depth remains future. |

## Recommended connector build order (next practical path)

1. Autotask hardening (contracts/projects/activities depth + webhooks where safe).
2. Xero live read path (contacts/invoices/payments with proper tenant/delta handling).
3. ITQuoter quote lifecycle connector (status transitions + quote-line commercial signals).
4. Microsoft Graph depth extension (usage/licence hygiene and confidence caveats).
5. Veeam VSPC-first backup posture slice.
6. 3CX CDR ingestion (relationship/cadence augmentation).

## Connector coverage matrix

| MSPIntel feature | Autotask | ITQuoter | Xero | M365 | Veeam | 3CX |
|---|---|---|---|---|---|---|
| Customer identity | yes | partial | partial | partial | partial | no |
| Contacts/stakeholders | yes | partial | partial | partial | no | partial |
| Ticket pressure | yes | no | no | no | partial | no |
| Quote lifecycle | partial | yes | no | no | no | no |
| Billing integrity | partial | partial | yes | partial | partial | no |
| Licence mismatch | no | no | no | yes | no | no |
| Backup posture | no | no | no | no | yes | no |
| Relationship health | partial | partial | no | partial | partial | yes |
| QBR prep | partial | partial | partial | partial | partial | partial |
| Risk engine | partial | partial | partial | partial | partial | partial |
| Marketing matching | partial | partial | partial | partial | partial | partial |

Legend: `yes` implemented/realistic path available; `partial` thin/demo/planned support; `no` not currently represented.
