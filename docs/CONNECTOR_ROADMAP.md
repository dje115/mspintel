# Connector Roadmap (plugin-style in-repo framework, v2.5 direction)

## Connector plugin contract (implemented)

- Every connector is an in-repo adapter implementing `ConnectorAdapter` and a strict `manifest` (`ConnectorManifest`).
- Manifest fields include key/display/family/maturity/auth modes/capabilities/sync modes/config fields/help text.
- Runtime validates `auth_mode` + required config keys using the connector manifest contract before save/test/sync.
- Catalog endpoint (`GET /api/v1/integrations/catalog`) is now metadata-rich and machine-readable for UI + feature gating.
- Shared utility `upsert_source_entity_mapping()` centralizes mapping writes.
- Manifests now also declare supported import-scope modes and scope filter keys for staged onboarding.

## Onboarding control layer (v2.7)

- Tenant connections now carry explicit lifecycle controls: `configured`, `tested`, `active`, `disabled`, `paused`, `error`.
- Sync behavior is explicit per connection: `manual_sync_only` or `scheduled_sync_enabled`.
- Import scope is explicit per connection (`all`, connector-specific scoped modes + filters), validated against manifest support.
- Mapping review queue (`/app/integrations/mappings`) enables human acceptance/rejection/remap/unlink on suggested identity matches.
- Coverage APIs expose unresolved and weak mapping counts for safer phased connector rollout.

## Maturity states

- `planned` — declared in catalog for roadmap visibility, no functional implementation.
- `stub` — explicit placeholder adapter; safe failure responses, no real data sync.
- `experimental` — partial implementation for thin slices or sandbox/demo paths.
- `beta` — implemented with deterministic tests, not yet broad production guarantee.
- `stable` — production-grade connector (target for later phases).

## Capability model

Canonical capability keys live in `backend/app/services/connectors/capabilities.py` and include:

- `customers`, `contacts`, `tickets`, `opportunities`, `quotes`
- `billing_accounts`, `invoices`
- `users`, `licences`, `mailboxes`, `storage`
- `backup_jobs`, `call_logs`
- `contracts`, `activities`, `notes`, `reviews`

Connectors declare capabilities in manifest metadata; product surfaces must stay honest about maturity and implementation.

## Current connector alignment

- **Autotask** (`beta`) — implemented PSA sync path for customers/contacts/tickets/opportunities/quotes.
- **Xero** (`experimental`) — implemented demo/sandbox finance materialization with clear non-live caveat.
- **Microsoft 365 / Entra** (`beta`) — implemented practical posture sync (demo-backed fallback; live depth intentionally limited).
- **ITQuoter** (`stub`) — declared manifest + safe failure behavior (auth metadata aligned to OAuth2/API-key reality).
- **Veeam / 3CX / ConnectWise / Sage / Azure** (`planned`/`stub`) — catalog-visible metadata for roadmap and UX gating.

Vendor API realism notes and Connector Lab alignment gaps are tracked in [CONNECTOR_VENDOR_SPEC_AUDIT.md](CONNECTOR_VENDOR_SPEC_AUDIT.md).

## Scaffold workflow

Use `backend/scripts/scaffold_connector.py` to create:
- provider module skeleton with manifest + stubbed `test_connection`/`run_sync`
- matching test scaffold file

Example:

`python backend/scripts/scaffold_connector.py --key sage --display-name "Sage Accounting" --family accounting --maturity planned --capabilities billing_accounts,invoices --auth-modes oauth2,sandbox`

## Guardrails

- Connector auth/config must declare secret vs non-secret fields.
- UI/catalog must not imply planned/stub connectors are production-ready.
- Keep connectors in-repo for now (plugin-like architecture, no untrusted dynamic external loading).
