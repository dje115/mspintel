# mspintel

mspintel is a secure, AI-assisted MSP intelligence platform for managed service providers. This repository provides a production-leaning, Docker-first SaaS multi-tenant scaffold with React, FastAPI, Python workers, PostgreSQL, and Redis.

## Stack

- Frontend: React + TypeScript (Vite)
- Backend API: FastAPI (app factory + modular packages)
- Worker: Python worker service scaffold
- Database: PostgreSQL 16
- Cache/Queue: Redis 7
- Runtime: Python 3.12
- Local orchestration: Docker Compose

## Repository Structure

- `frontend/` - UI scaffold prepared for public, app, platform admin, tenant admin, and onboarding areas
- `backend/` - FastAPI SaaS-oriented API structure
- `worker/` - Background worker foundation for async processing
- `docs/` - Architecture and development docs
- `compose.yaml` - Full local stack orchestration

## SaaS Multi-tenant Foundation

This scaffold is structured for true SaaS multi-tenancy from day one:

- `users` are global identities
- `tenants` are MSP workspaces
- `tenant_memberships` connect users to tenants with roles
- `plans` and `subscriptions` belong to tenants
- backend access context shape supports platform-role + tenant context evaluation

Included now:

- Core SaaS schema bootstrap SQL (`users`, `tenants`, `tenant_memberships`, `plans`, `subscriptions`)
- Backend module layout for platform, tenants, memberships, plans, subscriptions, onboarding
- Access context dependency (`user`, `tenant`, `platform role`) for future authz checks

Not fully implemented yet (by design):

- real signup and onboarding workflows
- payment provider integration
- full RBAC and tenant isolation middleware
- full tenant switch UX and management screens

## Local Setup (Docker-first)

1. Copy environment template:
   - `cp .env.example .env`
2. Start platform:
   - `docker compose up --build`
3. Access:
   - Frontend: <http://localhost:5173>
   - Backend health: <http://localhost:8001/health>
   - API health: <http://localhost:8001/api/v1/health>
   - Platform context probe: <http://localhost:8001/api/v1/platform/context>

## Run Services Individually

### Frontend

1. `cd frontend`
2. `npm install`
3. `npm run dev`

### Backend

1. `cd backend`
2. `python -m venv .venv`
3. Activate virtualenv
4. `pip install -e .[dev]`
5. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Worker

1. `cd worker`
2. `python -m venv .venv`
3. Activate virtualenv
4. `pip install -e .[dev]`
5. `python -m app.main`

## Tooling

- Frontend: ESLint + TypeScript checks
- Backend/Worker: Ruff setup
- Root: `.gitignore`, `.env.example`, Dockerfiles, Compose setup
