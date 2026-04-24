# Connector Roadmap (v2.1 foundation)

## Implemented now

- Connector abstraction: `ConnectorAdapter` with `test_connection()` and `run_sync()`.
- Runtime orchestration: `ConnectorRuntimeService` for connection CRUD, safe config handling, tests, manual sync triggers, and run history.
- Adapter registry: Autotask v1 + stubs for ITQuoter, ConnectWise, and Veeam.
- Mapping lineage: `source_entity_mappings` for source ID -> canonical entity ID.

## Autotask v1 scope

- Connection config + test flow (tenant-scoped, encrypted secrets).
- Sync paths:
  - Companies -> canonical customers
  - Contacts -> canonical contacts
  - Tickets -> canonical tickets
  - Opportunities -> canonical opportunities
  - Quotes -> canonical quotes (when endpoint available)
- Idempotent upsert behavior via canonical `external_ref` fields.
- Sync run lineage in `integration_sync_runs`.

## ITQuoter groundwork (not fully implemented)

- Registry/catalog entry included so UX can represent rollout.
- Planned entity focus:
  - quote headers + states
  - product/service line summaries
  - proposal lifecycle and conversion status
  - commercial-history signals for lost quote reactivation
- Intended product consumers:
  - `/app/opportunities` (lost/reactivation)
  - `/app/marketing` (campaign-ready commercial segments)
  - `/app/reviews` (QBR/account-development prep)

## ConnectWise / Veeam direction

- ConnectWise adapter should prioritize account/ticket/agreement ingestion with tenant-safe mapping.
- Veeam adapter should prioritize backup posture and job-health entities for service risk.
- Both can reuse the same runtime/mapping/run-history surfaces without API contract changes.

## Future connector model

- Keep each connector implementation in its own adapter module with minimal shared assumptions.
- Use `source_entity_mappings` + connector cursor metadata to support deterministic delta syncs.
- Add snapshot/warehouse facts as separate append-only tables once reporting needs exceed current-state UX queries.
