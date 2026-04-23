# mspintel

mspintel is a secure, AI-assisted MSP intelligence platform for MSPs. Release **`v1.2`** extends tenant lifecycle controls: membership role/status updates with guardrails, invitation expiry sweeper, session metadata and session management APIs/UI, and stronger API tests—while keeping the v1.1 access-control baseline (invitations, refresh rotation, audit, Mailpit).

## Stack

- Frontend: React + TypeScript + Vite + React Router
- Backend: FastAPI + SQLAlchemy + Alembic
- Auth: JWT access + refresh tokens with persisted session revocation
- Database: PostgreSQL 16
- Cache/queue: Redis 7
- Dev mail: Mailpit (SMTP + inbox UI)
- Worker: Python 3.12 poller (invitation expiry sweep; see [docs/WORKER.md](docs/WORKER.md))
- Orchestration: Docker Compose

## Versioning

- Current app version: **`1.2`**
- Central runtime version variable: `MSPINTEL_APP_VERSION` (root `.env` and Compose → backend `MSPINTEL_APP_VERSION`)
- Frontend display: `VITE_APP_VERSION` in `.env`, overridden in Compose from `MSPINTEL_APP_VERSION` as `VITE_APP_VERSION` for the dev container

## Multi-tenant Access Model

- `users` are global identities
- `tenants` are MSP workspaces
- `tenant_memberships` link users to tenant roles
- `tenant_invitations` manages invite lifecycle (`pending`, `accepted`, `expired`, `revoked`)
- `user_sessions` stores refresh sessions for revocation/rotation
- `plans` and `subscriptions` are tenant-owned billing foundations
- Platform admin remains distinct from tenant roles

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

## Local Run (Docker-first)

1. `cp .env.example .env`
2. `docker compose up --build -d`
3. `docker compose exec backend python -m app.db.seed` (first run / when you reset the DB)

The backend image runs **`alembic upgrade head` on container start**, so new migrations (e.g. session metadata columns) apply automatically after `docker compose up --build`. You can still run `docker compose exec backend alembic upgrade head` manually if needed.

**Browser → API in Compose:** the frontend dev server proxies `/api/*` to the `backend` service (`API_PROXY_TARGET`), and Compose sets `VITE_API_BASE_URL` to empty so the SPA calls **same-origin** `http://localhost:5173/api/...` (no cross-origin/CORS from the browser to `:8001`).

## Local URLs

- Frontend (app shell after login): [http://localhost:5173](http://localhost:5173)
- Tenant login: [http://localhost:5173/login](http://localhost:5173/login)
- Tenant signup: [http://localhost:5173/signup](http://localhost:5173/signup)
- **Platform admins use the same `/login` page** as tenant users (global `users` table + `is_platform_admin`).
- API health: [http://localhost:8001/health](http://localhost:8001/health)
- API v1 health: [http://localhost:8001/api/v1/health](http://localhost:8001/api/v1/health)
- Mailpit UI: [http://localhost:8025](http://localhost:8025)
- Mailpit SMTP: `mailpit:1025` (inside Docker network)

## Key Endpoints (Access-Control Slice)

- Auth/session:
  - `POST /api/v1/auth/signup`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
  - `POST /api/v1/auth/logout-all` (optional JSON `{"keep_refresh_token": "<current refresh>"}` to revoke only other sessions)
  - `GET /api/v1/auth/me`
  - `GET /api/v1/auth/sessions` (lists the caller’s refresh sessions with metadata; `is_current` uses the access token’s `sid` claim)
  - `POST /api/v1/auth/sessions/{session_id}/revoke` (not allowed for the current session; use `logout`)
- Tenant members/invitations:
  - `GET /api/v1/tenants/current/members`
  - `PATCH /api/v1/tenants/current/members/{membership_id}` (tenant role and/or `active` / `suspended` status; see `backend/app/domain/membership_rules.py`)
  - `GET /api/v1/tenants/current/invitations`
  - `POST /api/v1/tenants/current/invitations`
  - `POST /api/v1/tenants/current/invitations/{invitation_id}/revoke`
  - `POST /api/v1/invitations/accept`

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
- Access tokens include optional claim `sid` (session id) so the UI can highlight the current row.
- Refresh records `last_used_at` on the session being rotated; login/signup/refresh capture client IP and User-Agent when available.

## Session UI

- Authenticated users can open **Security** in the app shell (`/app/security`) to list sessions, revoke others, or **Sign out other sessions** (`logout-all` with `keep_refresh_token`).

## Tests added this phase

- `tests/test_membership_patch.py` — role updates, 403 for non-admin, cross-tenant 404, last-admin guard.
- `tests/test_invitation_sweep_repo.py` + `app/services/invitation_sweep.py` — idempotent expiry sweep.
- `tests/test_invitations.py` — extended edge cases (expired, revoked, duplicate accept, invalid token).
- `tests/test_sessions_list_revoke.py`, `tests/test_auth_sessions.py` — session list, revoke, logout-all keep-current.
- `tests/test_dashboard_tenant_scope.py`, `tests/test_repository_memberships.py` — tenant scoping and admin counting.

## App routes (frontend)

| Path | Purpose |
|------|---------|
| `/login` | Sign in |
| `/signup` | New tenant + owner signup |
| `/accept-invitation` | Accept invite (query `?token=`) |
| `/app` | Redirects to default app landing |
| `/app/onboarding` | Tenant onboarding |
| `/app/customers` | Customer list |
| `/app/customers/:id` | Customer detail |
| `/app/members` | Members + invitations management |
| `/app/security` | Sessions list / revoke / sign out others |
| `/app/system-status` | System status (requires `system:read`; shows API version) |

Dashboard JSON endpoints exist under `/api/v1/dashboards/*` (no dedicated SPA chart route yet).

## Validation Commands

- Backend tests: `cd backend && python -m pytest`
- Frontend build: `cd frontend && npm run build`
- Frontend lint: `cd frontend && npm run lint`
- Docker compose file: `docker compose config`
- **Note:** `alembic check` requires a reachable Postgres matching `DATABASE_URL` (e.g. with the stack up). Offline head: `cd backend && python -m alembic heads`.
