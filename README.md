# mspintel

mspintel is a secure, AI-assisted MSP intelligence platform. This repository provides the initial production-style foundation for a Docker-first web application with a React frontend, FastAPI backend, Python worker, PostgreSQL, and Redis.

## Stack

- Frontend: React + TypeScript (Vite)
- Backend API: FastAPI + Pydantic settings
- Worker: Python worker service (queue-ready structure)
- Database: PostgreSQL
- Cache/Queue: Redis
- Local orchestration: Docker Compose

## Repository Structure

- `frontend/` - React + TypeScript app
- `backend/` - FastAPI application
- `worker/` - Background job worker service
- `docs/` - Lightweight architecture and development docs
- `compose.yaml` - Full local stack orchestration

## Local Setup (Docker-first)

1. Copy environment template:
   - `cp .env.example .env`
2. Start the full platform:
   - `docker compose up --build`
3. Access services:
   - Frontend: <http://localhost:5173>
   - Backend health: <http://localhost:8001/health>
   - Backend API health: <http://localhost:8001/api/v1/health>

## Run Services Individually (without Docker)

### Frontend

1. `cd frontend`
2. `npm install`
3. `npm run dev`

### Backend

1. `cd backend`
2. `python -m venv .venv`
3. Activate the virtualenv
4. `pip install -e .[dev]`
5. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Worker

1. `cd worker`
2. `python -m venv .venv`
3. Activate the virtualenv
4. `pip install -e .[dev]`
5. `python -m app.main`

## Practical Tooling Included

- Frontend: ESLint + TypeScript checks
- Backend/Worker: Ruff formatter/linter config
- Root: `.gitignore`, `.env.example`, service Dockerfiles, compose stack

## Notes

This scaffold is intentionally lean. It is structured to support future modules such as auth, integrations, AI abstraction, adapter ingestion, and RBAC without locking in premature business logic.
