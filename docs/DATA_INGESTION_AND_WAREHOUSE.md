# Data Ingestion and Warehouse Direction (v2.1)

This phase introduces a real connector runtime foundation with Autotask v1 and a storage model that can grow into richer analytics without re-architecting.

**Strategic context:** connector priorities, per-system entity expectations, cadence philosophy, and how ingestion supports retention/commercial/billing product areas are summarised in **[MSP360_PRODUCT_SPEC.md](MSP360_PRODUCT_SPEC.md)** (especially §§17–18). Keep this technical doc aligned when the connector matrix changes materially.

## Data flow

1. Tenant admin configures a source connection in `/app/integrations`.
2. Config is encrypted at rest in `source_system_connections.encrypted_config`.
3. Connector runtime resolves an adapter by `system_type` (Autotask today; stubs for ITQuoter/ConnectWise/Veeam).
4. Sync run writes lifecycle into `integration_sync_runs` and updates connection health/status timestamps.
5. Adapter upserts canonical operational entities (`customers`, `contacts`, `tickets`, `opportunities`, optional `quotes`).
6. Source-to-canonical lineage is persisted in `source_entity_mappings`.

## Current storage tiers

- **Connection/config layer**  
  `source_system_connections` stores tenant-scoped connection metadata, cadence, health, and encrypted credentials/config.

- **Sync control plane**  
  `integration_sync_runs` records trigger mode, status, run timing, cursor, per-run stats JSON, and error summaries.

- **Mapping/reference layer**  
  `source_entity_mappings` keeps source entity IDs linked to canonical IDs by tenant + connection + entity type.

- **Canonical operational layer**  
  `customers`, `contacts`, `tickets`, `opportunities`, `quotes` continue as tenant-facing current-state records (now with optional `external_ref`; opportunities/quotes also carry title/value fields).

## Cadence model (first pass)

- **Connection test**: on demand (`POST /api/v1/integrations/connections/{id}/test`)
- **Manual sync**: on demand (`POST /api/v1/integrations/connections/{id}/sync`)
- **Scheduled sync design**: each connection now stores `sync_cadence_minutes` + `sync_mode`; runtime writes `trigger_mode` and cursor for future worker-driven scheduled deltas.
- **Initial/full sync**: run manual sync after onboarding a connector.
- **Delta sync**: adapter receives prior cursor (`connection_metadata.last_cursor`) and returns next cursor.

## Warehouse direction (next steps without rework)

The v2.1 model intentionally keeps the current app in a **canonical operational store first** pattern:

- Product pages query canonical tables directly for current-state UX.
- Historical/replay/analytics can be added by introducing append-only snapshot facts later, e.g.:
  - `warehouse_customer_daily_snapshot`
  - `warehouse_ticket_backlog_snapshot`
  - `warehouse_quote_stage_events`
- `integration_sync_runs` + `source_entity_mappings` already provide the lineage needed to backfill snapshots or verify source drift.

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
