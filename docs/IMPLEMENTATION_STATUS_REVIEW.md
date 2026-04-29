# Implementation status review (truth-based)

**As of:** seed refresh + codebase review (post–rich `demo-msp` dataset).  
**Method:** static review of routes, services, models, tests, and a small number of UI/API contracts — not a production load test.

## Workflow audit snapshot (2026-04-29, Docker-first)

- **Tenant routes:** Core auth, dashboard, customers, integrations, mappings, M365 health, billing integrity, recommendations, opportunities (incl. lost-quote tab redirect), at-risk/attention/service-risk, Review/QBR, AI settings — exercised via API/tests and **`v2.9.3+`** Playwright smoke (**`frontend/e2e/review-qbr-smoke.spec.ts`**: login, mappings, customers, Review tabs, mocked agenda/email/report + error banner); live Ollama remains optional/operator-owned.
- **Platform routes:** Login/tenants/connectors/prompts/audit — structurally present; MFA flows environment-dependent.
- **Review/QBR fix shipped in `v2.9.2`:** missing `tenant_ai_task_routes` rows caused **`AI_RUN_SKIPPED`** (“task disabled”) before users opened **AI engines**; resolver now **inserts stub routes** idempotently. UI shows an **orange outcome banner** when a run returns non-success. QBR variables include **`review_workspace.open_tickets`** (open ticket subjects) for PSA context.
- **Autotask:** Connector Lab–backed sync for accounts/contacts/tickets/opportunities/quotes is implemented in **`AutotaskConnectorAdapter`**; mapping review still gates new customers when a baseline already exists.
- **Xero thin import:** Not expanded in this slice; remains **next finance connector** priority after Autotask demo validation.

Classification used per area:

| Tag | Meaning |
|-----|--------|
| **Working** | End-to-end path exists; exercised by tests or obvious coherent code path. |
| **Rough** | Works but UX thin, error handling shallow, or metrics heuristic. |
| **Partial** | Real data/API slice; major spec gaps remain. |
| **Placeholder** | Route/shell present; little or no domain logic or backend persistence. |
| **Documented only** | Described in `MSP360_PRODUCT_SPEC.md` / other docs; no meaningful code. |
| **Broken / attention** | Known failure, unsafe default, or inconsistent behaviour observed in code review. |

---

## 1. Tenant-facing product UX

| Area | Status | What exists | Gaps / notes | Next |
|------|--------|-------------|--------------|------|
| Dashboard | **Partial** | KPIs from real counts (customers, high risk, open recs, lost quotes); links into workspaces. | “High risk” uses `account_scores` threshold in repo, not full ML; executive narrative mostly absent. | Richer widgets from `demo_profile` once surfaced in APIs. |
| Customers list | **Working** | Paginated list, status filter, scores, next action from first recommendation. | Search is simple `ILIKE`; no saved views. | Column for industry when exposed. |
| Customer 360 | **Partial** | Scores, counts, recs/opps/quotes tables, synced contact list, AI panels, AM guidance shell, **demo_profile** JSON panel when seeded. | No M365/backup/billing **live** tiles — narrative lives in `demo_profile` for demo only. | Domain panels when connectors ship. |
| Recommendations | **Working** | List, filters, patch status, AI explain with lineage. | Priority heuristic from scope only. | Owner assignment workflow. |
| Opportunities / quotes | **Working** | Commercial hub API + SPA tables from canonical rows. | No ITQuoter-native deep fields; `revisit_reason` partly static strings. | Lost-reason capture from PSA. |
| At-risk / Needs attention | **Working** | Queues by `Customer.status` + score columns. | Status is seed-driven; not computed pipeline. | Risk model + automated status transitions. |
| Service risk | **Partial** | Delivery section uses real open-ticket + at-risk counts. | Backup block is explicitly **placeholder** in `WorkspaceService.service_risk`. | Veeam connector + real job stats. |
| Reviews / QBR | **Working** (meeting-pack UX) | Tabbed workspace (`/app/reviews`): prep overview with **commercial cards** when opps/quotes exist, **AI agenda**, **AM prep as structured cards**, **email/report** with **persisted `output_warnings`** + **`quality_flags.needs_customer_review`**, **history** chips, **`GET …/context`**, **print CSS** aligned to `tenant-shell`; **`python -m app.scripts.sync_platform_prompt_defaults`** upserts missing **platform** prompt catalog without touching tenant overrides; missing prompt → **503** with remediation text. | No calendar sync; no editable long-form meeting notes DB; `GET …/ai/customer-review-agenda` remains legacy read of latest `ai_task_runs` only. | Calendar + collaborative notes. |
| Marketing | **Placeholder** | Shell, links, placeholder copy. | No idea bank DB, no matching engine. | Idea entity + segment API. |
| Data quality | **Placeholder** | Static shell pointing to Integrations. | No coverage scores API in tenant UI. | Sync health + coverage API. |
| Integrations | **Partial** | Connection list/detail, test + manual sync for supported types, sync run history, mapping review actions, and first-connector baseline import actions (create canonical customers from eligible mapping rows). | ConnectWise/Veeam/Sage still mostly **stub** adapters; **Autotask** and **M365 Connector Lab path** now have realistic thin sync flows plus reviewable identity states (`accepted`/`pending`/`unlinked`). | Harden CW + finance connectors. |
| AI settings | **Working** | Tenant AI settings PATCH, provider list, resolve, provider connectivity test action. | Provider “test” currently follows openai-compatible transport only; non-runnable families return explicit unsupported status. | Azure adapter when ready. |
| Prompts | **Working** | List definitions/versions, activate, tenant overrides, revert. | No diff UI / shadow mode. | Prompt compare tooling. |
| Roadmap | **Placeholder** | Static topic cards + placeholder detail. | No data binding. | OK as low priority. |

---

## 2. Platform admin

| Area | Status | Notes | Next |
|------|--------|-------|------|
| Platform login + MFA | **Working** | TOTP + recovery codes path; rate limits when Redis configured. | Redis-less dev weakens rate limit story. | Document Redis for prod-like dev. |
| Tenants overview | **Partial** | Lists tenants; operational not exhaustive. | Limited health metrics. | Tenant health from sync aggregates. |
| Platform AI providers / prompts | **Working** | Catalog CRUD, default prompts, versions. | — | — |
| Platform AI task runs | **Partial** | List recent runs with lineage columns. | Filtering/analytics basic. | Export + filters. |
| Platform security | **Partial** | Session list/revoke patterns per docs. | — | Align with tenant session UX parity. |
| Platform system status | **Rough** | Mirrors system health concept. | Depends on what backend exposes. | Deeper probes. |

---

## 3. Auth / tenancy / security

| Area | Status | Notes |
|------|--------|-------|
| Tenant auth (signup/login/refresh/logout) | **Working** | Covered by tests; tenant JWT cannot hit platform-only routes. |
| Platform auth | **Working** | Separate login + MFA track. |
| Memberships / invites | **Working** | Invite lifecycle + acceptance; audit events. |
| Sessions | **Working** | Revocation, rotation, `auth_mode` separation. |
| Tenant MFA | **Documented only / not in tenant login** | Platform MFA exists; tenant TOTP not the same product path. |
| Permission enforcement | **Working** | `require_permission` on APIs; role capability matrix in backend. |
| Audit model | **Partial** | Many mutations audited; not every read path logged (by design). |

---

## 4. AI system

| Area | Status | Notes |
|------|--------|-------|
| Provider configuration | **Working** | DB + catalog; encrypted settings. |
| Prompt registry / versioning | **Working** | Platform + tenant scopes; activation events. |
| Tenant overrides | **Working** | |
| Runtime execution | **Working** | OpenAI-compatible HTTP path; `ai_task_runs` lineage for product POSTs. |
| Unsupported providers | **Partial** | Clean `ProviderUnsupportedError` for some families. |
| Real AI-backed features today | **Partial** | Customer AI blocks + recommendation explain when provider configured and task enabled. |
| Placeholder-only | **Marketing / most roadmap** | No AI tasks wired there. |
| Maintainer / knowledge layer | **Documented only** | Spec §3; no `knowledge_objects` table or maintainer workers in code. |

---

## 5. Connectors / ingestion

| Connector | Status | Notes |
|-----------|--------|-------|
| Framework (connections, sync runs, mappings) | **Working** | Tables + APIs align with `DATA_INGESTION_AND_WAREHOUSE.md`. |
| Autotask | **Partial (beta adapter)** | Adapter + tests; Connector Lab connection test now validates base URL/auth/namespace/accounts endpoint and sync avoids silent duplicate customer creation when baseline exists (uses mapping review for unmatched rows). |
| ConnectWise | **Stub / planned** | Registry presence; no production ingestion path yet. |
| ITQuoter | **Stub** | Scaffold + updated auth metadata; live API integration still pending. |
| Veeam | **Stub / planned** | Scaffold; VSPC-first API direction documented. |
| Microsoft 365 | **Partial (practical slice)** | Tenant product has canonical M365 posture ingestion with Connector Lab-backed connection test/sync, explicit confidence notes, and live-depth limits for real Graph. Runtime demo seed is structural-only; posture rows appear after sync once mappings are confirmed/high-confidence or imported through first-connector baseline actions in mapping review. `/app/m365-health` now includes explicit AI summary/opportunity generation backed by canonical posture + tenant AI context and `ai_task_runs` lineage (not auto-run on load). |
| Accounting (Xero/Sage) | **Partial** | Canonical finance tables exist; Xero live ingestion remains limited and demo-backed. |
| Warehouse / snapshots | **Documented only** | No `warehouse_*` tables yet. |

---

## 6. Product intelligence (spec areas vs code)

| Intelligence area | Status | Reality |
|--------------------|--------|---------|
| Billing integrity | **Placeholder** | Finance connector depth is still limited; with structural-only seed, billing views depend on connector-synced canonical finance data and may be empty in demo until implemented syncs run. |
| Relationship health | **Partial** | Inferrable from tickets + contacts counts; no CDR/telephony. |
| Stalled work | **Partial** | Opportunities can be `stalled` status in seed; no dedicated stalled-work queue engine. |
| AM guidance | **Partial** | AI routes + UI shell; depends on LLM + prompt. |
| Campaign / event matching | **Placeholder** | Marketing shell only. |
| Data confidence | **Partial** | Coverage and confidence notes are exposed, but many domains remain connector-depth limited and can be empty after structural-only seed. |
| Backup posture | **Placeholder / connector-waiting** | Runtime seed does not inject backup facts; waits for connector sync depth. |
| Microsoft posture | **Partial (canonical + mock-backed)** | Canonical `m365_customer_postures` rows are populated from Connector Lab thin endpoints after sync; still not full live Graph depth. |

---

## 7. Spec / docs / roadmap

| Topic | Assessment |
|-------|------------|
| `MSP360_PRODUCT_SPEC.md` | **Ahead of code** in several domains (knowledge layer, finance, M365 depth). |
| `DATA_INGESTION_AND_WAREHOUSE.md` | **Aligned** with implemented connector tables; tier-4 knowledge still spec. |
| `AI_CONFIGURATION_AND_PROMPTS.md` | **Aligned** with runtime + maintainer direction. |
| Roadmap SPA | **Placeholder** by design. |

---

## 8. Runtime / Docker / development

| Topic | Status | Notes |
|-------|--------|-------|
| `docker compose config` | **Working** | Should be run after Compose edits. |
| Stack startup | **Working** | Typical path: up -d; backend runs Alembic + prompt ensure + optional seed. |
| Connector Lab mock APIs | **Working** | Dev-only `connector-lab` service exposes mock vendor namespaces + UI at `:8099` for connector/mapping testing without live vendor credentials. |
| Frontend stale bundle (Windows) | **Rough** | Documented in `CURSOR_RULES.md` (polling / restart). |
| Seed determinism | **Working** | `demo-msp` workspace fully replaced each `seed_all`; counts stable for a given `demo_rich_seed` version. |

---

## 9. Maturity summary table (concise)

| Pillar | Maturity |
|--------|----------|
| Multi-tenant auth / sessions / platform MFA | **Strong** |
| Core MSP CRM tables + workspace APIs | **Strong** |
| AI runtime + prompts + `ai_task_runs` | **Medium-strong** |
| Integrations UI + Autotask-shaped sync | **Medium** |
| Finance / M365 / backup **product** truth | **Medium-low (finance + M365 canonical slices, backup still stub-heavy)** |
| Marketing / data quality / stalled-work **product** surfaces | **Weak (mostly shells)** |
| Knowledge layer (persistent objects) | **None (spec only)** |

---

## 10. Five largest product gaps

1. **Backup canonical depth still missing** — finance and M365 now have practical canonical slices, but backup remains mostly placeholder/stub.  
2. **Marketing and campaign matching** — almost entirely non-functional beyond navigation.  
3. **Service-risk backup section** — explicitly placeholder despite customer need.  
4. **No automated risk/status** — `Customer.status` is seeded, not derived from rules across connectors.  
5. **Knowledge layer unimplemented** — spec’d architecture without storage or maintainer jobs.

---

## 11. Five recommended next phases (priority)

1. **Finance phase 0** — minimal `invoices` / `invoice_lines` or billing snapshot tables + one Xero read-only path; surface in 360.  
2. **Risk engine v1** — derive `attention_score` / status transitions from tickets + aged opps + demo finance hooks.  
3. **Marketing MVP** — idea entity + segment from customer filters + store match results.  
4. **Backup connector slice** — Veeam job sync into canonical + replace service-risk placeholder metrics.  
5. **Knowledge layer v0** — one object type (`customer_overview`) + maintainer task + read path in 360.

**Recommended to do first:** **Finance phase 0** (or **Risk engine v1** if you want faster visible “intelligence” without external API dependency). Finance unlocks honest billing/QBR narratives; risk engine improves dashboard and at-risk **without** claiming false precision.

**Before starting finance:** confirm **legal/API access** to Xero/Sage sandbox and decide **single source of truth** for customer ↔ finance account mapping (PSA account id vs accounting contact id).

---

## 12. Related doc

**[DEMO_SEED_DATA.md](DEMO_SEED_DATA.md)** — what the richer seed contains and how to reseed.
