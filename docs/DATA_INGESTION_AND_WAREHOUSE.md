# Data Ingestion and Warehouse Direction (v2.1)

This phase introduces a real connector runtime foundation with Autotask v1 and a storage model that can grow into richer analytics without re-architecting. Microsoft stack enrichment in `v2.8.0` extends this with practical M365/Entra canonical posture fields and billing-impact linkage.

**Strategic context:** connector priorities, per-system entity expectations, cadence philosophy, and how ingestion supports retention/commercial/billing product areas are summarised in **[MSP360_PRODUCT_SPEC.md](MSP360_PRODUCT_SPEC.md)** (especially **§3** persistent tenant knowledge layer, **§§18–19** data sources and warehouse strategy, and **§22** roadmap). The **four conceptual tiers** below align that spec with this technical doc—keep both files aligned when the connector matrix or knowledge model changes materially.

## Architecture tiers (conceptual)

| Tier | Description | Typical storage / artefacts today |
|------|-------------|-------------------------------------|
| **1. Raw synced source data** | Payloads and control data as produced by connectors—before or alongside normalisation into business rows | Encrypted `source_system_connections`, `integration_sync_runs`, adapter cursors/stats |
| **2. Source ↔ canonical mappings** | Stable links from external IDs to internal tenant rows | `source_entity_mappings` |
| **3. Canonical operational entities** | **Current-state** tenant tables that power queues, APIs, and Customer 360 counts | `customers`, `contacts`, `tickets`, `opportunities`, `quotes`, … — **source of truth** for operational facts |
| **4. Derived knowledge objects** | **Persistent**, tenant-scoped, **AI-maintained** summaries/narratives/postures (**not** a replacement for tier 3 facts). Refreshed on cadence or after sync; lineage via prompts + `ai_task_runs` | **Specified in product spec; not yet a first-class DB module** — future tables or document store TBD |
| **5. Historical snapshots / warehouse / analytics** | Append-only facts for trends and reporting without overloading tier 3 | Future: e.g. `warehouse_*_snapshot` facts; event streams |

**Why tier 4 matters:** product surfaces (360, QBR prep, marketing match, billing narrative) should not depend **only** on **query-time** RAG over raw rows or repeated one-off LLM synthesis. A **maintained knowledge layer** gives **stable narratives**, **staleness/evidence** semantics, and **governed prompt versions**—while tiers 1–3 remain authoritative for **what actually happened** in PSA, backup, M365, etc.

## Data flow

1. Tenant admin configures a source connection in `/app/integrations`.
2. Config is encrypted at rest in `source_system_connections.encrypted_config`.
3. Connector runtime resolves an adapter by `system_type` via the in-repo plugin registry (`ConnectorRegistry` + `ConnectorManifest`), including M365 v1 posture ingestion from Connector Lab (or demo fallback) in dev slices.
4. Sync run writes lifecycle into `integration_sync_runs` and updates connection health/status timestamps.
5. Adapter upserts canonical operational entities (`customers`, `contacts`, `tickets`, `opportunities`, optional `quotes`).
6. Source-to-canonical lineage is persisted in `source_entity_mappings`.
7. **(Future)** Successful sync completion or schedules **enqueue knowledge-object refresh** jobs for affected accounts (tier **4**)—see master spec maintenance lifecycle.

## Connector Lab support (development/testing)

For connector development without live vendor access, Compose includes a dev-only mock API service (`connector-lab`) reachable at:

- host: `http://localhost:8099`
- container DNS: `http://connector-lab:8099`

Connector Lab provides thin vendor namespaces (`/autotask`, `/itquoter`, `/xero`, `/m365`, `/veeam`, optional `/3cx`) with intentionally messy cross-system identity data and product-signal scenarios.
It now includes a few vendor-shape hints (for example Xero-style IDs and required `Xero-Tenant-Id` header checks) while remaining a pragmatic emulator rather than a full vendor clone.

This allows deterministic testing of:

- connector sync ingestion behavior (pagination, updated-since, partial fields)
- mapping confidence + review queue behavior (exact/near/unmatched/stale records)
- error handling (`401`, `429`, `500`, slow responses, empty datasets)
- downstream confidence and gap-to-action surfaces

Connector Lab is dev/test only and must not be treated as a production integration.
For current vendor-by-vendor audit findings and emulator gaps, see [CONNECTOR_VENDOR_SPEC_AUDIT.md](CONNECTOR_VENDOR_SPEC_AUDIT.md).

Current demo-data direction: keep app seed structural/config-only, and materialise connector-backed business telemetry via connector syncs from Connector Lab where implemented (starting with M365 posture).

## Current storage tiers (implementation)

- **Connection/config layer**  
  `source_system_connections` stores tenant-scoped connection metadata, cadence, health, encrypted credentials/config, and manifest-aligned metadata (`maturity`, `auth_modes`, `sync_modes`, `implemented`). Microsoft connector config remains redacted in all API responses.

- **Sync control plane**  
  `integration_sync_runs` records trigger mode, status, run timing, cursor, per-run stats JSON, and error summaries.

- **Mapping/reference layer**  
  `source_entity_mappings` keeps source entity IDs linked to canonical IDs by tenant + connection + entity type.

- **Canonical operational layer**  
  `customers`, `contacts`, `tickets`, `opportunities`, `quotes` continue as tenant-facing current-state records (now with optional `external_ref`; opportunities/quotes also carry title/value fields).
  Finance and Microsoft canonical tables (`finance_*`, `m365_customer_postures`) support billing integrity, M365 health, Customer 360, and QBR context. The Microsoft posture table now carries practical v1.5 fields: stale/disabled/privileged-user counts, tenant domains, usage summaries, and Entra/Azure summary JSON.

- **Derived knowledge layer (planned)**  
  Tenant-scoped **knowledge objects** (typed summaries linked to `customer_id` or tenant aggregates) **downstream of** canonical upserts. Populated by **maintainer** prompt runs, not by mutating tier 3 to “look like” AI output. **Ingestion’s role:** emit events or flags so refreshes run **after** data lands; **lint** jobs can compare objects to canonical facts for drift.

## Cadence model (first pass)

- **Connection test**: on demand (`POST /api/v1/integrations/connections/{id}/test`)
- **Manual sync**: on demand (`POST /api/v1/integrations/connections/{id}/sync`)
- **Scheduled sync design**: each connection now stores `sync_cadence_minutes` + `sync_mode`; runtime writes `trigger_mode` and cursor for future worker-driven scheduled deltas.
- **Initial/full sync**: run manual sync after onboarding a connector.
- **Delta sync**: adapter receives prior cursor (`connection_metadata.last_cursor`) and returns next cursor.

## Warehouse direction (next steps without rework)

The v2.1 model intentionally keeps the current app in a **canonical operational store first** pattern:

- Product pages query **canonical tables** (tier 3) directly for current-state UX today.
- **Knowledge objects** (tier 4) will sit **beside** canonical rows: reads compose **canonical facts + latest knowledge snapshot + freshness metadata**.
- Historical/replay/analytics (tier 5) can be added by introducing append-only snapshot facts later, e.g.:
  - `warehouse_customer_daily_snapshot`
  - `warehouse_ticket_backlog_snapshot`
  - `warehouse_quote_stage_events`
- `integration_sync_runs` + `source_entity_mappings` already provide the lineage needed to backfill snapshots, verify source drift, and **justify knowledge refresh** (what sync changed).

## ITQuoter and commercial roadmap grounding

- ITQuoter adapter is scaffolded in registry and catalog as a planned connector.
- Target canonical emphasis:
  - quote headers/states
  - product/service line summaries
  - proposal lifecycle changes
  - lost quote reasons and reactivation signals
- This aligns with `/app/opportunities`, `/app/marketing`, and future quote-reactivation automation.

## Security notes

- Sensitive connector config is encrypted with the existing integration encryption key path.
- API responses only expose redacted config (`safe_config`), never raw secrets.
- Error messages intentionally avoid echoing credentials or raw payloads.

## Plugin-style connector model (in-repo)

- This architecture is plugin-like but intentionally in-repo (no external untrusted plugin loading yet).
- Each connector declares a strict typed manifest:
  - connector key + display metadata
  - maturity (`planned`/`stub`/`experimental`/`beta`/`stable`)
  - supported auth modes
  - capability keys
  - sync modes
  - config field schema (required + secret flags)
- Runtime validates auth mode and required config fields using the connector manifest before persisting connection records.
- Runtime also validates connector-scoped import onboarding controls (scope mode + filters) against manifest-declared support.
- Connection runtime state now includes explicit lifecycle/sync behavior controls (`configured`/`tested`/`active`/`paused`/`disabled`/`error`, plus manual vs scheduled mode intent).
- Identity resolution includes a deterministic mapping-review layer (`connector_mapping_reviews`) for suggested customer matches, confidence levels, and auditable manual overrides. High-confidence matches may be auto-confirmed, while fuzzy/unmatched records should remain explicitly reviewable (`pending`/`unlinked`) instead of being silently canonicalised.
- First-connector baseline flow: when canonical customers are empty/low, mapping review supports a tenant-scoped, audited import action that creates canonical customers from eligible `pending`/`unlinked` source identities (selected rows or all eligible rows for a connector), then marks those mapping rows as accepted/confirmed.
- Current Autotask thin-slice behavior follows this rule: if baseline customers already exist, unmatched accounts are not auto-created and must pass mapping review before contacts/tickets/opportunities/quotes can link into canonical entities.
- Integrations catalog can consume this metadata directly for honest UX, docs, and future feature gating.
