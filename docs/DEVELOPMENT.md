# Development

**Ongoing implementation rules** (Docker-first, versioning, `.env.example`, validation, docs, GitHub reporting, tenant hero UX): see **[CURSOR_RULES.md](CURSOR_RULES.md)**. Future prompts and contributors should follow that document so setup and release discipline stay consistent.

## Prerequisites

- Docker + Docker Compose
- Python 3.12+ (for local backend testing)
- Node.js 20+ (for local frontend)

## Quick Start (Docker)

1. `cp .env.example .env` (set **`MFA_TOTP_ENCRYPTION_KEY`** to a Fernet key from `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` for any non-demo deployment; set a long random **`MFA_RECOVERY_CODE_PEPPER`** (≥16 chars) before relying on platform recovery codes in production)
2. `docker compose up --build -d` (the frontend dev image runs **`npm install`** on each container start so `node_modules` matches `package.json` after pulls; the app tree is bind-mounted at **`/src`** so Vite can serve the SPA route **`/app`** without colliding with the container workdir. If you ever need a clean install, `docker compose rm -sf frontend` then `docker compose up --build -d` recreates the anonymous `node_modules` volume.)
3. `docker compose exec backend alembic upgrade head` (optional: the backend entrypoint already runs `alembic upgrade head` on container start)
4. `docker compose exec backend python -m app.db.seed`

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
- Frontend build check: `cd frontend && npm run build`
- Frontend lint: `cd frontend && npm run lint`

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

- **Current app release: 1.8** (no bump in this hygiene pass; last bump shipped the tenant workspace slice).
- **Single operator-facing version** is driven by **`MSPINTEL_APP_VERSION`** (backend `settings.app_version`, Compose defaults for backend/worker/frontend, root `.env` / `.env.example`).
- **Frontend display string** uses **`VITE_APP_VERSION`** (set in `.env` or overridden in Compose from `MSPINTEL_APP_VERSION`); `frontend/src/config/version.ts` reads it for the tenant shell footer.
- **Python package** version: `backend/pyproject.toml` (`mspintel-backend`); **npm package** version: `frontend/package.json` — keep these aligned with the same release train when you cut a versioned build.

## Tenant product UX (local)

- Tenant-facing IA and wireframes: [TENANT_PRODUCT_WIREFRAMES.md](TENANT_PRODUCT_WIREFRAMES.md).
- Route ↔ layout map: [ROUTES_UX_MAP.md](ROUTES_UX_MAP.md).

## Platform MFA recovery codes (local)

- After seeding, enable TOTP on **`/platform/security`**, then generate recovery codes from the same page.
- **`POST /api/v1/auth/platform/login/mfa`** accepts either `totp_code` or `recovery_code` (see [PLATFORM_MFA.md](PLATFORM_MFA.md)).
- Rate limiting uses **Redis** (`PLATFORM_LOGIN_RATELIMIT_ENABLED`, `REDIS_URL`); see [PLATFORM_AUTH_HARDENING.md](PLATFORM_AUTH_HARDENING.md).
