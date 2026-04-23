# Development Workflow

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Node.js 20+ (for local frontend-only runs)
- Python 3.12+ (for local backend/worker-only runs)

## First Run

1. Copy env template:
   - `cp .env.example .env`
2. Start stack:
   - `docker compose up --build`
3. Verify:
   - Frontend: `http://localhost:5173`
   - Backend health: `http://localhost:8001/health`
   - API health: `http://localhost:8001/api/v1/health`
   - Platform context: `http://localhost:8001/api/v1/platform/context`

## Docker Commands

- Start: `docker compose up --build`
- Start detached: `docker compose up --build -d`
- Stop: `docker compose down`
- Remove volumes: `docker compose down -v`
- Logs: `docker compose logs -f`
- Status: `docker compose ps`

## Run Services Individually

### Frontend

- `cd frontend`
- `npm install`
- `npm run dev`

### Backend

- `cd backend`
- `python -m venv .venv`
- Activate virtualenv
- `pip install -e .[dev]`
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Worker

- `cd worker`
- `python -m venv .venv`
- Activate virtualenv
- `pip install -e .[dev]`
- `python -m app.main`

## Notes

- Postgres bootstrap SQL runs only on first initialization of the database volume.
- If schema bootstrap changes later, use migrations (recommended) rather than repeatedly recreating volumes.
