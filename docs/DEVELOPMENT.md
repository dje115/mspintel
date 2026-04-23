# Development Workflow

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend/worker development)

## Recommended Workflow

1. Copy env template:
   - `cp .env.example .env`
2. Start everything:
   - `docker compose up --build`
3. Iterate in code with mounted volumes (containers reload as configured).

## Useful Commands

- Start stack: `docker compose up --build`
- Stop stack: `docker compose down`
- Remove volumes: `docker compose down -v`
- View logs: `docker compose logs -f`

## Local Service Development

### Frontend

- `cd frontend`
- `npm install`
- `npm run dev`

### Backend

- `cd backend`
- `python -m venv .venv`
- `pip install -e .[dev]`
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Worker

- `cd worker`
- `python -m venv .venv`
- `pip install -e .[dev]`
- `python -m app.main`

## Next Recommended Milestones

- Add Alembic and first database migrations
- Add auth + RBAC primitives
- Introduce queue framework and first real async jobs
- Add API versioned routers for each domain area
- Add CI (lint, type-check, tests, image build)
