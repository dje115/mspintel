## 2026-04 Autotask + Customer 360 AI slice

- `account_manager_next_conversation.system` now receives richer connector-backed customer context, including synced contacts and open ticket snippets in addition to existing risk/commercial/M365/tenant-profile context.
- Customer-level AI runs remain explicit user-triggered from Customer 360 and continue to write lineage in `ai_task_runs`.
- Missing-provider and provider-failure states are surfaced as safe runtime outcomes (`unavailable` / `failed`) and routed back to `/app/ai-settings`.

# AI configuration and prompts

This document describes the **tenant-scoped AI engine configuration**, **task routing**, **versioned prompt registry**, and **runtime execution** (`v2.0+`) used by product features.

**Prompt key planning** for future product areas (relationship health, billing assurance, M365, backup, marketing, data quality, etc.) lives in **[MSP360_PRODUCT_SPEC.md](MSP360_PRODUCT_SPEC.md) §21** — add stable keys there (and to seed/catalog) when introducing new AI task types; avoid long hardcoded prompts in application code for user-facing templates.

**Persistent knowledge layer:** the product direction is to support **maintainer** (refresh) prompts that **update tenant-scoped knowledge objects**, not only **on-demand** completion prompts—see **§ Knowledge object maintenance** below and the master spec **§3** (persistent tenant knowledge layer).

**Tenant UI shells:** Review & QBR prep (`/app/reviews`), Marketing (`/app/marketing`), and the **AI account manager guidance** component label placeholder surfaces with the intended `*.system` keys so product and engineering stay aligned before runtime wiring.

---

## Runtime execution (`AIExecutionService`)

1. **`AIRuntimeResolver.resolve(tenant_id, task_type)`** — task route, default/fallback providers, active prompt version (tenant override or platform default).
2. **Prompt render** — `render_prompt_template` substitutes `{{placeholders}}` from a JSON-serializable variable map; the full map is also sent as the user message body for the chat call.
3. **Provider dispatch** — `execute_chat_completion` routes by `provider_family`. **Runnable today:** OpenAI-compatible HTTP (`openai`, `openrouter`, `ollama`, `vllm`, `lm_studio`, `openai_compatible`). **Adapter-ready / explicit unsupported:** `azure_openai` (needs dedicated wiring), `anthropic`, `google`, `microsoft_copilot`, `custom` (raise `ProviderUnsupportedError` without crashing the app).
4. **Persistence** — each product `POST` creates an **`ai_task_runs`** row: `queued` → `running` → terminal status (`succeeded`, `failed`, `unavailable`, `unsupported`, `skipped`). Lineage columns store provider family/mode, model, provider id, prompt definition/version ids, `fallback_used`, timestamps, optional `customer_id` / `recommendation_id`, `error_summary`, `output_summary`, and `run_metadata.assistant_text` for the full model output.

**Product endpoints (tenant):**

- `GET|POST /api/v1/customers/{id}/ai/account-summary`
- `GET|POST /api/v1/customers/{id}/ai/risk-summary`
- `GET|POST /api/v1/customers/{id}/ai/churn-explanation`
- `GET|POST /api/v1/customers/{id}/ai/customer-review-agenda`
- `GET|POST /api/v1/customers/{id}/ai/account-manager-next-conversation`
- `GET|POST /api/v1/customers/{id}/ai/account-manager-call-script`
- `GET|POST /api/v1/workspace/recommendations/{id}/ai/explanation`
- `GET /api/v1/workspace/m365-health/ai/latest`
- `POST /api/v1/workspace/m365-health/ai/summary`
- `GET /api/v1/workspace/m365-health/ai/opportunity/latest`
- `POST /api/v1/workspace/m365-health/ai/opportunity`

For the M365 workspace slice, generation is explicit user action from `/app/m365-health` (not page-load auto-run). Latest successful output is read from `ai_task_runs` state and includes provider/model/prompt lineage metadata.

**Platform observability:** `GET /api/v1/platform/ai/task-runs?limit=…`

---

## Knowledge object maintenance (maintainer prompts)

The prompt system is designed for **two complementary modes**:

| Mode | When it runs | Typical `prompt_key` pattern | Persisted output |
|------|----------------|------------------------------|------------------|
| **On-demand / user-facing** | User opens a panel or clicks “Generate” | e.g. `account_manager_next_conversation.system`, `billing_variance_summary.system` | Usually **`ai_task_runs`** (+ optional UI cache)—ephemeral unless separately saved |
| **Maintainer / knowledge refresh** | Schedule, **post-sync** trigger, operator batch, or prompt-version rollout | e.g. `customer_overview_maintainer.system` (see master spec **§21.7**) | **Knowledge object** store (future)—durable tenant artefact with **staleness**, **evidence pointers**, and **same lineage** fields as other runs |

**Requirements for implementers (directional):**

- **Maintainers use the same prompt DB** — `prompt_key`, `prompt_versions`, tenant overrides, and activation rules as on-demand tasks. **Do not** hardcode maintainer system text in workers when a keyed definition exists.
- **Each refresh should create or update `ai_task_runs`** (or a clearly linked child record) so **provider, model, prompt definition/version ids**, and outcome attach to the knowledge object for audit.
- **User-facing prompts** should **prefer reading** the latest valid knowledge object **plus** a small window of canonical facts for deltas, rather than re-synthesising the entire account from scratch on every request—when the object exists and is fresh enough (policy TBD).
- **Task types** for maintainers will need **routing rows** (`tenant_ai_task_routes`) and, when wired, **worker or API** entrypoints distinct from interactive `POST …/ai/...` customer endpoints—implementation TBD; this doc establishes the **contract** with the product spec.

Cross-links: [DATA_INGESTION_AND_WAREHOUSE.md](DATA_INGESTION_AND_WAREHOUSE.md) (tier 4 derived knowledge), master spec **§3** (knowledge layer) and **§19** (warehouse & ingestion).

---

## Provider taxonomy

Each logical provider is described with:

- **`provider_family`**: `openai`, `azure_openai`, `anthropic`, `google`, `microsoft_copilot`, `openrouter`, `ollama`, `vllm`, `lm_studio`, `openai_compatible`, `custom`, …
- **`deployment_mode`**: `hosted`, `self_hosted`, `local`, `microsoft`

Together they drive filtering and badges in the UI (for example: self-hosted Ollama vs hosted OpenAI).

Tenant-facing provider rows (`ai_providers`) store **encrypted** JSON settings (API keys, endpoints). API responses use **redacted** settings and never return ciphertext or raw secrets.

Demo/dev seed defaults are env-driven (`AI_DEFAULT_PROVIDER`, `AI_DEFAULT_MODE`, `AI_DEFAULT_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_DEFAULT_MODEL`) so local Ollama can be the initial provider without hardcoding.

---

## Task routing

Stable **`AI_TASK_TYPES`** (for example `ticket_triage`, `email_draft`) each have a **`tenant_ai_task_routes`** row:

- optional provider/model and fallback
- **`prompt_key`** (stable string, e.g. `ticket_triage.system`)
- **`enabled`** flag

On first read, missing routes are materialised with sensible defaults so tenants do not have to pre-seed every row.

Runtime resolution (`AIRuntimeResolver`) returns the effective provider family, deployment mode, model, and the **active** prompt version (see below) for a `(tenant_id, task_type)` pair.

---

## Prompt inheritance and versioning

- **Platform definitions** (`scope=platform`, `tenant_id` null): global defaults, keyed by `prompt_key`.
- **Tenant overrides** (`scope=tenant`, `tenant_id` set): same `prompt_key` as a platform row; when present, the tenant definition wins for resolution.

**Versions** live in `prompt_versions` (append-only). Activating a version deactivates siblings for that definition. Tenants can:

- create a new version on their override
- activate a previous version (rollback)
- delete the override (revert-to-default) to fall back to the platform active version

API list responses intentionally omit full `prompt_text` on version rows where not needed; the **resolve** endpoint can include prompt text for authorised callers building runners.

---

## Permissions

| Capability | Roles |
|------------|--------|
| `ai:view` | `tenant_admin`, `director`, `sales_user`, `account_manager`, `service_manager`, `marketing_user`, `platform_admin` |
| `ai:configure` | `tenant_admin`, `platform_admin` |

Platform-only routes require a **platform** JWT (`am=platform`) and `is_platform_admin`.

All mutations are enforced server-side; the UI only hides controls for clarity.

---

## Audit events (non-secret)

Examples include `ai.tenant_settings.updated`, `ai.task_route.updated`, `ai.prompt.version_created`, `ai.prompt.version_activated`, `ai.prompt.reverted_to_platform_default`, and platform catalog / prompt lifecycle events. Patches in audit payloads are JSON-safe (UUIDs as strings); secrets are never logged.

---

## API surface (summary)

**Tenant** (`X-Tenant-Id` + tenant session):

- `GET|PATCH /api/v1/ai/settings`
- `GET|PATCH /api/v1/ai/task-routes`
- `GET /api/v1/ai/providers`, `POST /api/v1/ai/providers`
- `POST /api/v1/ai/providers/{id}/test` (safe connectivity/model smoke check; returns message for unreachable local providers such as host Ollama)
- `GET /api/v1/ai/resolve/{task_type}`
- `GET /api/v1/prompts`, `GET /api/v1/prompts/{id}`, versions, activate, tenant-overrides, revert-to-default

**Platform**:

- `GET|POST /api/v1/platform/ai/providers/catalog`
- `GET|POST /api/v1/platform/prompts`, versions, activate

---

## UI routes

| Area | Path |
|------|------|
| Tenant AI settings | `/app/ai-settings` |
| Tenant prompts | `/app/prompts` |
| Platform provider catalog | `/platform/ai-providers` |
| Platform default prompts | `/platform/prompts` |

Warning copy is shown on AI and prompt surfaces: changes affect behaviour, cost, privacy, and quality; rollback is supported but not instantaneous for in-flight work.

---

## Migrations and seed

Alembic revision **`0009_ai_cfg_prompts`** adds catalog, tenant settings/routes, prompt tables, and extends `ai_task_runs` with lineage columns. Revision **`0010_ai_task_runs_exec`** adds execution metadata (`error_summary`, `output_summary`, `fallback_used`, `started_at`, `completed_at`, `actor_user_id`, `customer_id`, `recommendation_id`). `seed_all` calls `ensure_ai_provider_catalog`, `ensure_platform_default_prompts`, **`ensure_legacy_prompt_aliases`** (e.g. clone `customer360.summary` → `account_summary.system` when needed), and aligns the demo tenant provider row where applicable.

After pulling: `cd backend && alembic upgrade head` (or rely on Docker entrypoint).
