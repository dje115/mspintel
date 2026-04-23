# mspintel

mspintel is a secure, AI-assisted MSP intelligence platform for MSPs. This release (`v1.1`) hardens SaaS access control with invitation workflows, stricter permissions, refresh/session revocation, audit logging, and Mailpit-backed development email.

## Stack

- Frontend: React + TypeScript + Vite + React Router
- Backend: FastAPI + SQLAlchemy + Alembic
- Auth: JWT access + refresh tokens with persisted session revocation
- Database: PostgreSQL 16
- Cache/queue: Redis 7
- Dev mail: Mailpit (SMTP + inbox UI)
- Worker: Python 3.12 scaffold
- Orchestration: Docker Compose

## Versioning

- Current app version: `1.1`
- Central runtime version variable: `MSPINTEL_APP_VERSION` (root `.env`)
- Frontend display version variable: `VITE_MSPINTEL_APP_VERSION` (set from `MSPINTEL_APP_VERSION` in Compose)

## Multi-tenant Access Model

- `users` are global identities
- `tenants` are MSP workspaces
- `tenant_memberships` link users to tenant roles
- `tenant_invitations` manages invite lifecycle (`pending`, `accepted`, `expired`, `revoked`)
- `user_sessions` stores refresh sessions for revocation/rotation
- `plans` and `subscriptions` are tenant-owned billing foundations
- Platform admin remains distinct from tenant roles

## Security and Hardening in v1.1

- Server-side permission enforcement with role capability checks
- Tenant-scoped invitation/member endpoints and query filtering
- Refresh token rotation with old session invalidation
- Logout revokes current refresh session; logout-all revokes all sessions
- Existing-account invite acceptance requires login as invited identity
- Invitation/member change audit events are persisted in `audit_events`
- Raw invitation token exposure is disabled by default (`EXPOSE_INVITATION_TOKEN_IN_RESPONSE=false`)

## Local Run (Docker-first)

1. `cp .env.example .env`
2. `docker compose up --build -d`
3. `docker compose exec backend alembic upgrade head`
4. `docker compose exec backend python -m app.db.seed`

## Local URLs

- Frontend: [http://localhost:5173](http://localhost:5173)
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
  - `POST /api/v1/auth/logout-all`
  - `GET /api/v1/auth/me`
- Tenant members/invitations:
  - `GET /api/v1/tenants/current/members`
  - `GET /api/v1/tenants/current/invitations`
  - `POST /api/v1/tenants/current/invitations`
  - `POST /api/v1/tenants/current/invitations/{invitation_id}/revoke`
  - `POST /api/v1/invitations/accept`

## Validation Commands

- Backend tests: `cd backend && python -m pytest`
- Frontend build: `cd frontend && npm run build`
- Frontend lint: `cd frontend && npm run lint`
