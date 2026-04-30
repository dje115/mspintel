# Development

**Ongoing implementation rules** (Docker-first, versioning, `.env.example`, validation, docs, GitHub reporting, tenant hero UX): see **[CURSOR_RULES.md](CURSOR_RULES.md)**. Future prompts and contributors should follow that document so setup and release discipline stay consistent.

**Product direction** (customer intelligence scope, connectors, prompt planning, roadmap): **[MSP360_PRODUCT_SPEC.md](MSP360_PRODUCT_SPEC.md)**.

## Prerequisites

- Docker + Docker Compose
- Python 3.12+ (for local backend testing)
- Node.js 20+ (for local frontend)

## Quick Start (Docker)

1. `cp .env.example .env` (set **`MFA_TOTP_ENCRYPTION_KEY`** to a Fernet key from `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` for any non-demo deployment; set a long random **`MFA_RECOVERY_CODE_PEPPER`** (≥16 chars) before relying on platform recovery codes in production)
2. `docker compose up --build -d` (the frontend dev image runs **`npm install`** on each container start so `node_modules` matches `package.json` after pulls; the app tree is bind-mounted at **`/src`** so Vite can serve the SPA route **`/app`** without colliding with the container workdir. Dependencies live on the named Compose volume **`frontend_node_modules`**; to reset only that volume, see README “Frontend image” / Rollup troubleshooting.)
3. `docker compose exec backend alembic upgrade head` (optional: the backend entrypoint already runs `alembic upgrade head` on container start)
4. `docker compose exec backend python -m app.db.seed`
5. **Optional (existing DBs after pulling new prompt keys):** `docker compose exec backend python -m app.scripts.sync_platform_prompt_defaults` — upserts **missing** platform prompt definitions/versions and repairs platform rows missing an active version; **does not** wipe tenants or overwrite tenant prompt overrides. The backend container entrypoint also runs this catalog sync after migrations on start.
6. **Task routes:** the runtime resolver auto-creates default **`tenant_ai_task_routes`** stubs for known task types (same as opening **AI engines**), so Review/QBR generation is not blocked before the first visit to AI settings (`v2.9.2+`).

### Docker smoke check (tenant workspace)

After the stack is up and seeded:

1. **Backend:** `curl -s -o NUL -w "%{http_code}" http://localhost:8001/health` → `200`.
2. **Tenant APIs:** log in with `POST /api/v1/auth/login` (demo tenant admin), then with `Authorization: Bearer …` and `X-Tenant-Id: <tenant uuid>` call `GET /api/v1/workspace/recommendations`, `GET /api/v1/workspace/commercial`, and `GET /api/v1/workspace/service-risk` — each should return **200** JSON.
3. **Frontend:** open [http://localhost:5173/app](http://localhost:5173/app) in a browser, or `curl -s -I http://localhost:5173/app` and confirm **HTTP 200**. You should get the SPA shell, not a Vite **500** (that symptom was the old container workdir **`/app`** clashing with the route **`/app`**; fixed by **`/src`** in `frontend/Dockerfile` + `compose.yaml`).

## Mailpit (Local Dev Email)

- UI: [http://localhost:8025](http://localhost:8025)
- SMTP host/port for backend (Docker network): `mailpit:1025`
- Invitation mails should appear in Mailpit after create-invite requests.

## Tests and Checks

- Backend tests: `cd backend && python -m pytest`
- Frontend unit tests (display helpers): `cd frontend && npm run test`
- Frontend build check: `cd frontend && npm run build`
- Frontend lint: `cd frontend && npm run lint`

### Playwright browser smoke (Review / QBR)

Automated **user-journey** checks live in **`frontend/e2e/review-qbr-smoke.spec.ts`**. **`e2e/global-setup.ts`** logs in via **`POST /api/v1/auth/login`** against **`E2E_API_BASE_URL`** (default **`http://127.0.0.1:8001`**) and writes Playwright **`storageState`** to **`frontend/e2e/.auth/tenant.json`** (gitignored), plus **`e2e/.cache/meta.json`** with the first customer id (if any). If the tenant has **no customers** yet, global-setup **triggers one `Microsoft 365 (Connector Lab)` manual sync** (same as Integrations → Sync) and re-reads customers so Review/QBR tests can run against a populated demo — set **`E2E_SKIP_CONNECTOR_PREP=1`** to skip that (e.g. offline API-only checks).

**Prerequisites**

- Docker Compose stack up; backend on host port **8001** and Vite on **5173** (default Compose publish).
- Demo seed applied (`docker compose exec backend python -m app.db.seed`) and, for full Review assertions, at least **one customer** (Connector Lab M365 sync + mapping import as in **[DEMO_SEED_DATA.md](DEMO_SEED_DATA.md)**).

**Install browser once (host)**

```bash
cd frontend
npm run test:e2e:install
```

**Run smoke (host, mocked Review AI — no Ollama)**

By default, Review AI **POST** responses for agenda / email / report are **stubbed in the browser** (`page.route`) so CI and laptops without a model still prove the SPA wiring, copy controls, persistence reload, and history list. Unset the default mock with **`E2E_MOCK_AI=0`** to hit the real backend provider (then you need a working tenant AI provider).

```bash
cd frontend
set E2E_API_BASE_URL=http://127.0.0.1:8001
set PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173
npm run test:e2e
```

(On PowerShell, `set` → `$env:E2E_API_BASE_URL="http://127.0.0.1:8001"`.)

**Pass / skip conditions**

- **Always:** dashboard with seeded session; mappings page heading; customers empty-state **or** row navigation; optional **UI login** test (isolated context, demo credentials).
- **When `meta.customerId` exists:** Review tabs visible; **503** agenda path shows the orange **outcome** region and mentions AI settings / provider.
- **When `E2E_MOCK_AI` is not `0` and a customer exists:** agenda/email/report generation assertions, reload keeps email subject, **AI history** lists artefact types.

**Optional live Ollama / real provider smoke (manual)**

1. Configure tenant **AI engines** per **[AI_CONFIGURATION_AND_PROMPTS.md](AI_CONFIGURATION_AND_PROMPTS.md)** so the backend can reach Ollama (or another OpenAI-compatible endpoint) from the **backend** container (`host.docker.internal` or compose `extra_hosts` as needed).
2. `cd frontend` → `E2E_MOCK_AI=0 E2E_API_BASE_URL=http://127.0.0.1:8001 npm run test:e2e` — expect longer runtimes; failures may reflect model latency or provider errors rather than UI regressions.
3. Manually verify **`/app/ai-settings`** “test provider” and **`/app/reviews`** email generation if you want human confirmation beyond automated tests.

## Connector development (plugin-style, in-repo)

- Contract lives in `backend/app/services/connectors/base.py` + `manifest.py`.
- Capabilities are standardized in `backend/app/services/connectors/capabilities.py`.
- Registry/runtime uses manifest metadata for catalog and config validation.
- Scaffold a new connector with:
  - `cd backend`
  - `python scripts/scaffold_connector.py --key "<key>" --display-name "<Name>" --family "<family>" --maturity planned --capabilities customers --auth-modes api_key`
- After scaffolding, wire adapter into `ConnectorRegistry`, implement `test_connection()` and `run_sync()`, and add deterministic tests.

## Connector Lab (dev-only vendor emulator)

Connector Lab runs as a Compose service (`connector-lab`) and provides mock vendor APIs plus a browser UI for connector development/testing without live vendor credentials.

- UI: `http://localhost:8099/`
- Status: `http://localhost:8099/ui/status`
- Health: `http://localhost:8099/health`
- Container DNS from backend/worker: `http://connector-lab:8099`

### Auth

Use either:

- `Authorization: Bearer ${CONNECTOR_LAB_TOKEN}` (default: `connector-lab-dev-token`)
- `X-API-Key: ${CONNECTOR_LAB_API_KEY}` (default: `connector-lab-api-key`)

### Mock namespaces

- `/autotask`, `/itquoter`, `/xero`, `/m365`, `/veeam`, `/3cx` (thin optional)

### Supported testing behavior

- pagination (`page`, `page_size`)
- `updated_since` filtering
- forced modes via `mode=` query and/or `X-Connector-Lab-Mode` header:
  - `auth_failure`
  - `rate_limit`
  - `server_error`
  - `slow`
  - `empty`
  - `partial`

### Scenario usage

Use `/ui/scenarios` and `/ui/signals` to inspect:

- cross-system customer mismatches (exact, near match, suffix/trading-name differences, unmatched, stale/legacy variants)
- realistic UK-style customer naming (no generic "Scenario Customer" labels) with vendor-specific variants
- product signal conditions (billing-vs-M365 mismatch, inactive licensed users, failed/stale backup jobs, overdue restore tests, lost/stalled quotes, aged debt)

### Pointing connectors at Connector Lab

Set connection base URLs (or environment hints) to:

- `AUTOTASK_BASE_URL=http://connector-lab:8099/autotask`
- `AUTOTASK_API_KEY=connector-lab-api-key`
- `ITQUOTER_BASE_URL=http://connector-lab:8099/itquoter`
- `XERO_BASE_URL=http://connector-lab:8099`
- `XERO_TENANT_ID=demo-tenant-id`
- `XERO_ACCESS_TOKEN=connector-lab-dev-token` (or `CONNECTOR_LAB_API_KEY`)
- `M365_BASE_URL=http://connector-lab:8099/m365`
- `VEEAM_BASE_URL=http://connector-lab:8099/veeam`

Use this service for development/testing only. It is not a production vendor integration endpoint.

### M365 mock realism notes

- Vendor-like Graph-inspired endpoints: `/m365/organization`, `/m365/users`, `/m365/subscribedSkus`, `/m365/users/{id}/licenseDetails`.
- Connector Lab convenience endpoints (`/m365/licence-summary`, `/m365/mailbox-counts`, `/m365/hygiene-findings`) remain for thin-slice reporting and are not full Graph clones.
- Dev-only mapping metadata is exposed separately at `/m365/lab-scenarios`; normal vendor endpoints do not expose MSPIntel control fields.

## Local Ollama default for demo/dev AI

- Demo seed can initialize tenant AI defaults from env (no hardcoded provider): `AI_DEFAULT_PROVIDER`, `AI_DEFAULT_MODE`, `AI_DEFAULT_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_DEFAULT_MODEL`.
- Docker Desktop default host access is `http://host.docker.internal:11434` (not `localhost` from inside containers).
- Validate in `/app/ai-settings` using provider **Test** action; unreachable Ollama returns a safe error message without crashing routes.

### Demo sync orchestration (current thin-slice flow)

Preferred flow for connector-backed demo domains:

1. Seed structural/config baseline: `docker compose exec backend python -m app.db.seed`
2. Log in as tenant admin (`tenant-admin@demo-msp.example.com`)
3. From Integrations, test/sync connector connections (start with M365 baseline, then Xero), or call:
   - `POST /api/v1/integrations/connections/{id}/test`
   - `POST /api/v1/integrations/connections/{id}/sync`
4. Validate canonical surfaces:
   - `GET /api/v1/integrations/mappings` (reviewable suggested/unlinked identity rows)
   - `POST /api/v1/integrations/mappings/create-customers` (selected/all eligible first-connector baseline import)
   - `GET /api/v1/workspace/m365-health`
   - `GET /api/v1/workspace/billing-integrity`
   - `/app/integrations/mappings`
   - Use "Create customers from all eligible rows" (or selected rows) in mapping review when starting from an empty customer baseline.
   - `/app/customers` (verify imported canonical customers exist)
   - Run a Xero sync, then verify `/app/integrations/mappings` includes Xero contact rows and `/app/billing-integrity` shows finance cards
   - Run an Autotask sync, then verify `/app/customers/{id}` has connector-synced contacts plus service/commercial counts
   - `/app/m365-health`
   - Use **Generate AI hygiene summary** / **Generate AI opportunity guidance** in `/app/m365-health` after linked posture rows exist
   - If generation fails, verify provider health in `/app/ai-settings` and test the configured default provider

The direction is to keep seed mostly structural and let connector syncs materialise realistic business telemetry into canonical tables.
Runtime demo seed should not directly create synthetic customer/ticket/finance/posture rows.

## Migration Commands

- Upgrade: `docker compose exec backend alembic upgrade head`
- Current revision: `docker compose exec backend alembic current`
- Downgrade one step: `docker compose exec backend alembic downgrade -1`

## Coverage Added in This Hardening Pass

- signup tenant+membership creation
- invitation create/list permission enforcement
- invite acceptance (new user + existing-account restriction)
- tenant-scoped customer access and cross-tenant denial
- refresh rotation, logout revocation, logout-all revocation
- invitation acceptance audit-event verification

## Versioning

- **Current app release** is driven by **`MSPINTEL_APP_VERSION`** — see **[README.md](../README.md)** (Versioning) and **`compose.yaml`** defaults for the live number.
- **Single operator-facing version** flows to backend `settings.app_version`, Compose, root `.env` / **`.env.example`**, and frontend **`VITE_APP_VERSION`** (tenant shell footer via `frontend/src/config/version.ts`).
- **Python package** version: `backend/pyproject.toml` (`mspintel-backend`); **npm package** version: `frontend/package.json` — keep these aligned with the same release train when you cut a versioned build.

## Tenant product UX (local)

- Tenant-facing IA and wireframes: [TENANT_PRODUCT_WIREFRAMES.md](TENANT_PRODUCT_WIREFRAMES.md).
- Route ↔ layout map: [ROUTES_UX_MAP.md](ROUTES_UX_MAP.md).

## Platform MFA recovery codes (local)

- After seeding, enable TOTP on **`/platform/security`**, then generate recovery codes from the same page.
- **`POST /api/v1/auth/platform/login/mfa`** accepts either `totp_code` or `recovery_code` (see [PLATFORM_MFA.md](PLATFORM_MFA.md)).
- Rate limiting uses **Redis** (`PLATFORM_LOGIN_RATELIMIT_ENABLED`, `REDIS_URL`); see [PLATFORM_AUTH_HARDENING.md](PLATFORM_AUTH_HARDENING.md).
