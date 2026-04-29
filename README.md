# mspintel

mspintel is a secure, AI-assisted MSP intelligence platform for MSPs. Release **`v2.9.0`** added the **Review & QBR workspace** (`/app/reviews`): tabbed meeting-pack UI, connector-shaped context, prompt-driven **AI agenda / AM prep / customer email / customer report**, **persisted `customer_review_ai_artifacts`** with **`short_context_json`** for continuity, and **`ai_task_runs`** lineage. **`v2.9.1`** hardens that workspace with **non-destructive platform prompt catalog sync**, clearer **missing-prompt errors**, **commercial snapshot cards**, **account-manager card layout**, **placeholder / fenced-output warnings** (persisted and surfaced), and **print CSS aligned to the tenant shell**. **`v2.9.2`** fixes a **first-run Review/QBR AI gap**: **`tenant_ai_task_routes` stubs are created automatically** when resolving any known `AI_TASK_TYPES` task (same defaults as opening **AI engines**), so **email/report/agenda generation works without pre-visiting AI settings**, and Review/QBR variables include a short **open-tickets preview** for PSA-backed context. **`v2.9.3`** adds a **Playwright browser smoke** for login → **Integration mappings** → customers → **Review/QBR** tabs and AI flows (**mocked** Review AI by default so CI does not need Ollama), and fixes **Review workspace “Mappings” links** to **`/app/integrations/mappings`**. The product remains on **`v2.8.0`** Microsoft stack foundations (M365 health, Customer 360, billing integrity).

## Implementation guidance (Cursor / contributors)

Standing rules for Docker, versioning, env vars, validation, docs, GitHub workflow, reporting, and tenant-vs-platform UX: **[docs/CURSOR_RULES.md](docs/CURSOR_RULES.md)**. Use that file as the default checklist for future implementation work.

**Master product specification** (vision, roles, product matrix, data sources, prompt keys, maturity, roadmap): **[docs/MSP360_PRODUCT_SPEC.md](docs/MSP360_PRODUCT_SPEC.md)**.

## Stack

- Frontend: React + TypeScript + Vite + React Router
- Backend: FastAPI + SQLAlchemy + Alembic
- Auth: JWT access + refresh tokens with persisted session revocation
- Database: PostgreSQL 16
- Cache/queue: Redis 7
- Dev mail: Mailpit (SMTP + inbox UI)
- Worker: Python 3.12 poller (invitation expiry sweep; see [docs/WORKER.md](docs/WORKER.md))
- Connector Lab: Docker-hosted mock vendor API emulator + dev UI (`http://localhost:8099`) for connector development/testing without live vendor access
- Orchestration: Docker Compose

## Versioning

- Current app version: **`2.9.3`** (Playwright Review/QBR smoke + mapping link fix; builds on 2.9.2 Review AI routing)
- Central runtime version variable: `MSPINTEL_APP_VERSION` (root `.env` and Compose → backend `MSPINTEL_APP_VERSION`)
- Frontend display: `VITE_APP_VERSION` in `.env`, overridden in Compose from `MSPINTEL_APP_VERSION` as `VITE_APP_VERSION` for the dev container

## Multi-tenant Access Model

- `users` are global identities
- `tenants` are MSP workspaces
- `tenant_memberships` link users to tenant roles
- `tenant_invitations` manages invite lifecycle (`pending`, `accepted`, `expired`, `revoked`)
- `user_sessions` stores refresh sessions for revocation/rotation
- `plans` and `subscriptions` are tenant-owned billing foundations
- Platform admin (`users.is_platform_admin`) remains distinct from tenant roles; **v1.3+** enforces separate sign-in, JWT scope (`am`), and (from **v1.4**) distinct refresh session rows and TTL policy for platform vs tenant (see [docs/PLATFORM_SESSIONS_AND_AUDIT.md](docs/PLATFORM_SESSIONS_AND_AUDIT.md)).

## Security and Hardening (v1.1 baseline + v1.2 extensions)

- Server-side permission enforcement with role capability checks
- Tenant-scoped invitation/member endpoints and query filtering
- Refresh token rotation with old session invalidation
- Logout revokes current refresh session; logout-all revokes all sessions
- Existing-account invite acceptance requires login as invited identity
- Invitation/member change audit events are persisted in `audit_events`
- Raw invitation token exposure is disabled by default (`EXPOSE_INVITATION_TOKEN_IN_RESPONSE=false`)
- **v1.2:** Membership PATCH validates roles/status, blocks last active `tenant_admin` removal, normalizes role codes, skips no-op updates (no audit noise).
- **v1.2:** Session list/revoke is strictly user-scoped; revoking the **current** session is rejected (use `POST /auth/logout` with refresh token).
- **v1.2:** `logout-all` JSON body is validated; invitation sweeper uses UTC-aware cutoff in the ORM path.
- **v1.3:** Tenant `POST /auth/login` rejects platform-admin accounts (they must use `POST /auth/platform/login`). Access tokens carry claim `am` = `tenant` \| `platform`; tenant APIs reject `am=platform`. Platform APIs require `am=platform` and `is_platform_admin`.
- **v1.4:** Tenant vs platform **access/refresh TTL** env vars; `user_sessions.auth_mode`; session APIs scoped by `am`; platform audit events with `tenant_id` null; `/platform/security`. See [docs/PLATFORM_SESSIONS_AND_AUDIT.md](docs/PLATFORM_SESSIONS_AND_AUDIT.md).
- **v1.5:** Platform **TOTP MFA** for operator accounts only; tenant `/auth/login` unchanged. Encrypted TOTP secrets, step tokens for login/enrolment, policy flag `PLATFORM_MFA_REQUIRED`. See [docs/PLATFORM_MFA.md](docs/PLATFORM_MFA.md).
- **v1.6:** MFA **hardening** (Fernet key validation at settings load, failed-challenge audit `reason` codes, migration/docs clarity) and version **1.6** across Compose defaults and UI version tags (`VITE_APP_VERSION` / `MSPINTEL_APP_VERSION`).
- **v1.7:** Platform **recovery codes** for MFA (pepper + HMAC storage, `/platform/security` UX), **`POST /platform/mfa/recovery-codes/generate`**, MFA step accepts **`recovery_code`** or **`totp_code`**, **Redis rate limits** on platform login/MFA with **429** + `platform.login.rate_limited` audit, operational docs in [docs/PLATFORM_AUTH_HARDENING.md](docs/PLATFORM_AUTH_HARDENING.md). Tenant `/auth/login` unchanged.
- **v1.8:** Tenant **`/api/v1/workspace`** routes (recommendations list + admin patch, commercial hub, service-risk snapshot); customer detail includes typed **recommendations / opportunities / quotes**; SPA operational pages under `/app/recommendations`, `/app/opportunities`, `/app/at-risk`, `/app/attention`, `/app/service-risk`; dashboard KPIs link into these workspaces.
- **v1.9:** Tenant AI **`/api/v1/ai/*`**, prompts **`/api/v1/prompts/*`**, platform catalog/prompts **`/api/v1/platform/ai/*`** and **`/api/v1/platform/prompts/*`**; Alembic **`0009_ai_cfg_prompts`**; SPA **`/app/ai-settings`**, **`/app/prompts`**, **`/platform/ai-providers`**, **`/platform/prompts`**. See [docs/AI_CONFIGURATION_AND_PROMPTS.md](docs/AI_CONFIGURATION_AND_PROMPTS.md).
- **v2.0:** **`AIExecutionService`** + OpenAI-compatible **HTTP adapter** (OpenAI, OpenRouter, Ollama, vLLM, LM Studio, generic `openai_compatible`); **stub/unsupported** path for Azure (until dedicated adapter), Anthropic, Google, Microsoft Copilot, custom; product APIs **`POST /api/v1/customers/{id}/ai/*`** and **`POST /api/v1/workspace/recommendations/{id}/ai/explanation`**; Alembic **`0010_ai_task_runs_exec`**; SPA Customer 360 **AI insights**, recommendations **Explain**, platform **`/platform/ai-task-runs`**.

## Local Run (Docker-first)

1. `cp .env.example .env`
2. `docker compose up --build -d`
3. `docker compose exec backend python -m app.db.seed` (first run / when you reset the DB — seeds structural/config baseline and Connector Lab connection bootstrap; see [docs/DEMO_SEED_DATA.md](docs/DEMO_SEED_DATA.md))
4. For connector-backed slices (starting with M365), run connector sync from Integrations or API (`POST /api/v1/integrations/connections/{id}/sync`) so canonical rows are populated from Connector Lab payloads.

**Implementation audit (what is real vs placeholder):** [docs/IMPLEMENTATION_STATUS_REVIEW.md](docs/IMPLEMENTATION_STATUS_REVIEW.md)

The backend image runs **`alembic upgrade head` on container start**, then **idempotently ensures platform default prompt rows** (including new task keys as they ship), so new migrations and prompt stubs apply automatically after `docker compose up --build`. You can still run `docker compose exec backend alembic upgrade head` manually if needed.

**Migrations without relying on container startup:** from the repo root, with Compose up, run `docker compose exec backend alembic upgrade head`. For a **local** backend venv, `cd backend`, set `DATABASE_URL` to your Postgres DSN (for the default Compose DB: `postgresql+psycopg://mspintel:mspintel@127.0.0.1:5432/mspintel`), then `python -m alembic upgrade head`.

**Browser → API in Compose:** the frontend dev server proxies `/api/*` to the `backend` service (`API_PROXY_TARGET`), and Compose sets `VITE_API_BASE_URL` to empty so the SPA calls **same-origin** `http://localhost:5173/api/...` (no cross-origin/CORS from the browser to `:8001`). The frontend container uses **`WORKDIR /src`** and bind-mounts **`./frontend:/src`** so the tenant route **`/app`** never collides with the filesystem path `/app` (which previously caused Vite **500** / `EISDIR` on `GET /app`).

**Frontend image:** **`node:20-bookworm-slim`** (glibc). Vite 5 / Rollup 4 need a matching **native** `@rollup/rollup-*` package inside Linux containers. Alpine (`musl`) plus npm’s optional-dependency behaviour could crash Vite with `Cannot find module '@rollup/rollup-linux-x64-musl'`; even on Debian, a persisted volume could hit `Cannot find module '@rollup/rollup-linux-x64-gnu'` when npm skips an optional transitive. **`frontend/package.json`** therefore declares **`optionalDependencies.@rollup/rollup-linux-x64-gnu`** (installed in Docker/Linux, skipped on Windows host installs). Compose keeps `node_modules` on the named volume **`frontend_node_modules`**. To reset only that volume: `docker compose stop frontend`, `docker volume rm <project>_frontend_node_modules` (see `docker volume ls`; default project name is the repo folder), then `docker compose up --build -d`. Avoid `docker compose down -v` unless you accept wiping Postgres/Redis data volumes too.

## Local URLs

| Surface | URL |
| --- | --- |
| Tenant login | [http://localhost:5173/login](http://localhost:5173/login) |
| Tenant signup | [http://localhost:5173/signup](http://localhost:5173/signup) |
| Tenant dashboard (after login) | [http://localhost:5173/app](http://localhost:5173/app) |
| Product roadmap (placeholder hub) | [http://localhost:5173/app/roadmap](http://localhost:5173/app/roadmap) |
| Recommendations queue | [http://localhost:5173/app/recommendations](http://localhost:5173/app/recommendations) |
| Opportunities & quotes | [http://localhost:5173/app/opportunities](http://localhost:5173/app/opportunities) |
| At-risk accounts | [http://localhost:5173/app/at-risk](http://localhost:5173/app/at-risk) (Risk Engine v1 queue) |
| Needs attention | [http://localhost:5173/app/attention](http://localhost:5173/app/attention) (Risk Engine v1 queue) |
| Service risk | [http://localhost:5173/app/service-risk](http://localhost:5173/app/service-risk) |
| Integrations | [http://localhost:5173/app/integrations](http://localhost:5173/app/integrations) |
| Integration detail pattern | `http://localhost:5173/app/integrations/<connection-id>` |
| Data quality | [http://localhost:5173/app/data-quality](http://localhost:5173/app/data-quality) |
| Marketing, events & campaigns | [http://localhost:5173/app/marketing](http://localhost:5173/app/marketing) |
| Review & QBR prep | [http://localhost:5173/app/reviews](http://localhost:5173/app/reviews) (optional account context: `?customer_id=<uuid>`) |
| M365 health | [http://localhost:5173/app/m365-health](http://localhost:5173/app/m365-health) |
| Tenant AI settings | [http://localhost:5173/app/ai-settings](http://localhost:5173/app/ai-settings) |
| Tenant prompts | [http://localhost:5173/app/prompts](http://localhost:5173/app/prompts) |
| Tenant customers | [http://localhost:5173/app/customers](http://localhost:5173/app/customers) |
| Customer 360 | From [customers](http://localhost:5173/app/customers), open any account row once connector sync has populated customer data. In current demo strategy, runtime seed is structural-only and connector-backed telemetry is loaded via Connector Lab syncs (M365 first). See [docs/DEMO_SEED_DATA.md](docs/DEMO_SEED_DATA.md). Example: `http://localhost:5173/app/customers/<customer-uuid>?ai=risk` (risk AI). **Prepare review:** `/app/reviews?customer_id=<customer-uuid>`. |
| **Platform console login** | [http://localhost:5173/platform/login](http://localhost:5173/platform/login) |
| **Platform console** | [http://localhost:5173/platform](http://localhost:5173/platform) |
| **Platform AI provider catalog** | [http://localhost:5173/platform/ai-providers](http://localhost:5173/platform/ai-providers) |
| **Platform default prompts** | [http://localhost:5173/platform/prompts](http://localhost:5173/platform/prompts) |
| **Platform AI task runs** | [http://localhost:5173/platform/ai-task-runs](http://localhost:5173/platform/ai-task-runs) |
| **Platform security / sessions** | [http://localhost:5173/platform/security](http://localhost:5173/platform/security) |
| Connector Lab UI (dev-only) | [http://localhost:8099](http://localhost:8099) |
| Connector Lab status | [http://localhost:8099/ui/status](http://localhost:8099/ui/status) |

- API health: [http://localhost:8001/health](http://localhost:8001/health)
- API v1 health: [http://localhost:8001/api/v1/health](http://localhost:8001/api/v1/health)
- Mailpit UI: [http://localhost:8025](http://localhost:8025)
- Mailpit SMTP: `mailpit:1025` (inside Docker network)

## Connector Lab (dev-only mock vendor APIs)

Connector Lab is a Docker-hosted emulator used for connector development and mapping-confidence testing without hitting live vendor APIs.

- UI overview: `http://localhost:8099/`
- Status page: `http://localhost:8099/ui/status`
- Health endpoint: `http://localhost:8099/health`
- Auth (for JSON API calls):  
  - `Authorization: Bearer ${CONNECTOR_LAB_TOKEN}` (default `connector-lab-dev-token`)  
  - or `X-API-Key: ${CONNECTOR_LAB_API_KEY}` (default `connector-lab-api-key`)

Mock namespaces currently available:

- `/autotask` — accounts, contacts, tickets, opportunities, quotes
- `/itquoter` — customers, quotes, quote lines, quote statuses
- `/xero` — contacts, invoices, invoice lines, payment statuses
- `/m365` — Graph-inspired organization/users/subscribedSkus/licenseDetails + convenience summary endpoints
- `/veeam` — customers, backup jobs, workloads, repositories, restore tests
- `/3cx` — calls, extensions (thin optional namespace)

Example curl:

- `curl -H "Authorization: Bearer connector-lab-dev-token" "http://localhost:8099/autotask/accounts?page=1&page_size=2"`
- `curl -H "Authorization: Bearer connector-lab-dev-token" -H "Xero-Tenant-Id: demo-tenant-id" "http://localhost:8099/xero/invoices?mode=rate_limit"`
- `curl -H "Authorization: Bearer connector-lab-dev-token" "http://localhost:8099/m365/users?updated_since=2026-01-01T00:00:00Z"`

Autotask connection tests in this slice support both credential styles:
- Connector Lab style: `base_url=${AUTOTASK_BASE_URL}` + `api_key=${AUTOTASK_API_KEY}` (or Connector Lab bearer token).
- Vendor-style Autotask REST: `base_url` + `integration_code` + `username` + `secret`.

Connector Lab includes expanded identity and signal scenarios (name mismatches, unmatched records, stale/deleted hints, billing-vs-M365 gaps, failed backups, aged debt) to validate mapping review and data-confidence behavior. M365 mapping-control metadata is exposed only on dev-only scenario endpoints, not vendor-shaped payloads. It is the preferred source of realistic connector-backed demo data where connector syncs are implemented. See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) and [docs/DATA_INGESTION_AND_WAREHOUSE.md](docs/DATA_INGESTION_AND_WAREHOUSE.md).

### Local Ollama demo default (env-driven)

- Demo/dev seed can initialize the first tenant provider from env (`AI_DEFAULT_PROVIDER`, `AI_DEFAULT_MODE`, `AI_DEFAULT_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_DEFAULT_MODEL`).
- For Docker Desktop, use `OLLAMA_BASE_URL=http://host.docker.internal:11434` so containers reach host Ollama.
- Verify provider connectivity from `/app/ai-settings` using the provider **Test** button.

## Key Endpoints (Access-Control Slice)

- Auth/session:
  - `POST /api/v1/auth/signup`
  - `POST /api/v1/auth/login` (tenant users only; **403** if `is_platform_admin`)
  - `POST /api/v1/auth/platform/login` (platform admins only; **401** if not authorized—same message for wrong password or non-admin; response includes `outcome`: `authenticated` \| `mfa_challenge` \| `mfa_enrollment_setup` — tokens are returned only when `outcome` is `authenticated`)
  - `POST /api/v1/auth/platform/login/mfa` (body: `mfa_challenge_token` and **either** `totp_code` **or** `recovery_code`; returns normal token pair after successful second factor; **429** if rate limited)
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
  - `POST /api/v1/auth/logout-all` (optional JSON `{"keep_refresh_token": "<current refresh>"}`; works with **tenant** or **platform** access token—no `X-Tenant-Id` required for platform sessions)
  - `GET /api/v1/auth/me` (returns `auth_mode`: `tenant` \| `platform` from the JWT; does not require tenant membership)
  - `GET /api/v1/auth/sessions` (only sessions matching the caller’s JWT `am`; each row includes `auth_mode`; `is_current` uses access token `sid`)
  - `POST /api/v1/auth/sessions/{session_id}/revoke` (not allowed for the current session; use `logout`; cannot revoke a session from the other scope; optional `X-Tenant-Id` when auditing a **tenant** revoke)
- Platform (Bearer token must be **platform** session; see `get_platform_admin` in `backend/app/api/deps/access.py`):
  - `GET /api/v1/platform/overview`
  - `GET /api/v1/platform/tenants?page=&page_size=`
  - `GET /api/v1/platform/system-status`
  - `GET /api/v1/platform/mfa/status`
  - `POST /api/v1/platform/mfa/totp/enrollment` (Bearer: platform access **or** short-lived `mfa_enroll` setup token from login when MFA is required but TOTP not yet enabled)
  - `POST /api/v1/platform/mfa/totp/enrollment/confirm`
  - `POST /api/v1/platform/mfa/totp/disable` (platform access only; requires valid TOTP; clears recovery codes)
  - `POST /api/v1/platform/mfa/recovery-codes/generate` (platform access only; TOTP must be enabled; returns plaintext codes **once**)
- Tenant members/invitations:
  - `GET /api/v1/tenants/current/members`
  - `PATCH /api/v1/tenants/current/members/{membership_id}` (tenant role and/or `active` / `suspended` status; see `backend/app/domain/membership_rules.py`)
  - `GET /api/v1/tenants/current/invitations`
  - `POST /api/v1/tenants/current/invitations`
  - `POST /api/v1/tenants/current/invitations/{invitation_id}/revoke`
  - `POST /api/v1/invitations/accept`
- Tenant workspace (Bearer **tenant** JWT + `X-Tenant-Id`; `customer:read` unless noted):
  - `GET /api/v1/workspace/recommendations` — query: `page`, `page_size`, optional `status`, `scope`, `customer_id`, `owner`
  - `PATCH /api/v1/workspace/recommendations/{recommendation_id}` — body `{"status":"open"|"accepted"|"rejected"|"completed"}`; requires **`membership:write`** (typically `tenant_admin`)
  - `GET /api/v1/workspace/commercial` — opportunities + lost + open/draft quotes for the commercial hub
  - `GET /api/v1/workspace/service-risk` — backup placeholder section + live delivery metrics (e.g. open tickets, at-risk count)
  - `GET /api/v1/workspace/risk-queue?mode=at_risk|attention` — ranked Risk Engine v1 queues (scores, reasons, confidence, next-step placeholder)
  - `POST /api/v1/workspace/risk-engine/recompute` — on-demand risk recompute (tenant batch; optional `customer_id` for single account)
  - `GET /api/v1/workspace/m365-health` — Microsoft 365 hygiene/licence posture workspace (thin v1, coverage-aware)
  - `GET /api/v1/workspace/m365-health/ai/latest` — latest portfolio M365 AI hygiene summary state
  - `POST /api/v1/workspace/m365-health/ai/summary` — explicit M365 AI hygiene generation (connector-backed canonical context)
  - `GET /api/v1/workspace/m365-health/ai/opportunity/latest` — latest M365 AI opportunity guidance state
  - `POST /api/v1/workspace/m365-health/ai/opportunity` — explicit M365 AI opportunity generation
  - `GET /api/v1/integrations/catalog` — connector catalog with manifest metadata (maturity, auth modes, capabilities, sync modes, config field schema)
  - `GET /api/v1/integrations/connections` — tenant-scoped connection list
  - `POST /api/v1/integrations/connections` — create connector config (**membership:write**)
  - `PATCH /api/v1/integrations/connections/{connection_id}` — update connector config (**membership:write**)
  - `POST /api/v1/integrations/connections/{connection_id}/test` — test credentials/config safely (**membership:write**)
  - `POST /api/v1/integrations/connections/{connection_id}/sync` — trigger manual sync run (**membership:write**)
  - `GET /api/v1/integrations/connections/{connection_id}/runs` — list recent sync run history

## Tenant membership updates

- Tenant admins (and platform operators) with `membership:write` may `PATCH` a membership in the **current** tenant only.
- Rules are documented in `backend/app/domain/membership_rules.py` (assignable roles, `active`/`suspended`, and **last active `tenant_admin` guard**).
- Changes emit `membership.updated` audit events with before/after role and status.

## Invitation expiry sweeper

- **Backend (canonical, tested):** `InvitationRepository.expire_pending_past_expiry()` and `sweep_expired_invitations()` in `backend/app/services/invitation_sweep.py` mark `pending` invitations with `expires_at` in the past as `expired` (idempotent).
- **Worker (Docker):** each poll runs the same logic for Postgres via `UPDATE … WHERE status = 'pending' AND expires_at < NOW()` in `worker/app/jobs/runner.py`. Details: [docs/WORKER.md](docs/WORKER.md).
- Run the stack with `docker compose up` and watch `mspintel-worker` logs for `invitation_sweep expired_rows=…`. After schema changes, run `docker compose exec backend alembic upgrade head`.

## Session metadata

- Alembic `0004_session_metadata` adds `ip_address`, `user_agent`, `device_label`, and `last_used_at` to `user_sessions`.
- Alembic `0006_user_mfa_methods` adds platform-operator TOTP MFA storage ([docs/PLATFORM_MFA.md](docs/PLATFORM_MFA.md)).
- Alembic `0007_platform_mfa_recovery_codes` adds hashed platform recovery codes ([docs/PLATFORM_MFA.md](docs/PLATFORM_MFA.md)).
- Alembic `0008_plat_mfa_rc_hash_ix` adds `(user_id, code_hash)` index for verification lookups.
- Access tokens include optional claim `sid` (session id) so the UI can highlight the current row.
- **v1.3:** Access and refresh tokens include claim `am` (`tenant` \| `platform`) so tenant APIs cannot be used with a platform-console session and vice versa. Refresh preserves `am`. Legacy tokens without `am` are treated as tenant scope for compatibility.
- **v1.4:** `user_sessions.auth_mode` mirrors JWT scope; logout-all only revokes matching `auth_mode` rows. **TTL:** `TENANT_*` vs `PLATFORM_*` env vars (see `.env.example` and [docs/PLATFORM_SESSIONS_AND_AUDIT.md](docs/PLATFORM_SESSIONS_AND_AUDIT.md)).

## Platform vs tenant (routing)

- **Tenant SPA:** `/login`, `/signup`, `/accept-invitation`, `/app/...` — normal MSP workspace users.
- **Platform SPA:** `/platform/login`, `/platform`, `/platform/tenants`, `/platform/system-status`, `/platform/security` — `is_platform_admin` users only, with platform-scoped JWTs.
- Same deployment and user table; enforcement is **server-side** (JWT + flags) with **frontend route guards** for UX (`TenantProtectedRoute`, `PlatformProtectedRoute`).

### Demo credentials (local Docker / seed)

Run `docker compose exec backend python -m app.db.seed` after the database is up. Then use:

| Role | Email | Password | Sign-in URL |
|------|--------|----------|-------------|
| **Tenant MSP admin** (demo workspace) | `tenant-admin@demo-msp.example.com` | `ChangeMe123!` | [http://localhost:5173/login](http://localhost:5173/login) |
| **Platform operator** | `admin@mspintel.example.com` | `ChangeMe123!` | [http://localhost:5173/platform/login](http://localhost:5173/platform/login) |

Defaults match `SEED_PLATFORM_ADMIN_*` and the demo tenant in `backend/app/services/seed.py`. Override via `.env` if needed.

Tenant and platform accounts use **separate** login URLs (tenant JWT cannot call tenant APIs with `am=platform`, and vice versa).

### Product UX docs (tenant)

- [docs/TENANT_PRODUCT_WIREFRAMES.md](docs/TENANT_PRODUCT_WIREFRAMES.md) — information architecture and page wireframes for the MSP workspace.
- [docs/ROUTES_UX_MAP.md](docs/ROUTES_UX_MAP.md) — which layout wraps which routes (public tenant auth vs `AppLayout` vs platform console).

## Session UI

- Authenticated users can open **Security** in the app shell (`/app/security`) to list sessions, revoke others, or **Sign out other sessions** (`logout-all` with `keep_refresh_token`).

## Tests added this phase

- `tests/test_platform_recovery_and_ratelimit.py` — recovery-code hashing, MFA substitute, single-use, regeneration, audits, platform rate limit **429**, tenant login unaffected.
- `tests/test_platform_mfa.py` — platform TOTP enrolment, login challenge, policy `PLATFORM_MFA_REQUIRED`, audits, tenant login unchanged.
- `tests/test_membership_patch.py` — role updates, 403 for non-admin, cross-tenant 404, last-admin guard.
- `tests/test_invitation_sweep_repo.py` + `app/services/invitation_sweep.py` — idempotent expiry sweep.
- `tests/test_invitations.py` — extended edge cases (expired, revoked, duplicate accept, invalid token).
- `tests/test_sessions_list_revoke.py`, `tests/test_auth_sessions.py` — session list, revoke, logout-all keep-current.
- `tests/test_dashboard_tenant_scope.py`, `tests/test_repository_memberships.py` — tenant scoping and admin counting.
- `tests/test_workspace_api.py` — workspace list tenant scope, commercial + service-risk reads, recommendation PATCH permission model.

## App routes (frontend)

| Path | Purpose |
|------|---------|
| `/login` | Tenant MSP sign-in (distinct visual system from platform login) |
| `/signup` | New tenant + owner signup |
| `/accept-invitation` | Accept invite (query `?token=`) |
| `/app` | **Dashboard** — executive KPIs (linked) + priority lists + panel CTAs to operational workspaces |
| `/app/recommendations` | Recommendations queue |
| `/app/opportunities` | Opportunities & quotes hub (`?tab=`) |
| `/app/at-risk` | At-risk account workspace |
| `/app/attention` | Needs-attention (watch) workspace |
| `/app/service-risk` | Backup & service risk overview |
| `/app/onboarding` | Tenant onboarding |
| `/app/customers` | Accounts & customers directory (`?status=` supported) |
| `/app/customers/:id` | Customer 360 / account intelligence (`#workspace` → recommendations tab) |
| `/app/members` | Team & invitations |
| `/app/integrations` | Integration connections |
| `/app/integrations/mappings` | Mapping review queue (import baseline, accept/reject, filters) |
| `/app/security` | Sessions list / revoke / sign out others |
| `/app/system-status` | System status (requires `system:read`; shows API version) |

## Validation Commands

- Backend tests: `cd backend && python -m pytest`
- Frontend build: `cd frontend && npm run build`
- Frontend lint: `cd frontend && npm run lint`
- **Browser smoke (Playwright):** with Docker Compose up and demo seed (customers present), from the repo host: `cd frontend && npm run test:e2e:install` once, then `E2E_API_BASE_URL=http://127.0.0.1:8001 npm run test:e2e` (details: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#playwright-browser-smoke-review--qbr)).
- Docker compose file: `docker compose config`
- **Note:** `alembic check` requires a reachable Postgres matching `DATABASE_URL` (e.g. with the stack up). Offline head: `cd backend && python -m alembic heads`.
