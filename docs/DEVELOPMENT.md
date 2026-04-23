# Development

## Prerequisites

- Docker + Docker Compose
- Python 3.12+ (for local backend testing)
- Node.js 20+ (for local frontend)

## Quick Start (Docker)

1. `cp .env.example .env` (set **`MFA_TOTP_ENCRYPTION_KEY`** to a Fernet key from `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` for any non-demo deployment)
2. `docker compose up --build -d` (the frontend dev image runs **`npm install`** on each container start so `node_modules` matches `package.json` after pulls; if you ever need a clean install, `docker compose rm -sf frontend` then `docker compose up --build -d` recreates the anonymous `node_modules` volume.)
3. `docker compose exec backend alembic upgrade head` (optional: the backend entrypoint already runs `alembic upgrade head` on container start)
4. `docker compose exec backend python -m app.db.seed`

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

- Current release: `1.1`
- Keep `MSPINTEL_APP_VERSION` and `VITE_MSPINTEL_APP_VERSION` aligned for each Docker/platform release update.
