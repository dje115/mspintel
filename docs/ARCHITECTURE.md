# mspintel Architecture (Initial Scaffold)

## Services

- **frontend** (`React + TypeScript + Vite`)
  - User-facing web interface
  - Prepared for responsive dashboard-oriented UI
  - Talks to backend through configurable API base URL

- **backend** (`FastAPI`)
  - HTTP API layer
  - Current endpoints:
    - `/health`
    - `/api/v1/health`
  - Package layout anticipates future modules:
    - auth, users, integrations, customers, tickets, recommendations, ai

- **worker** (`Python service`)
  - Background task entrypoint
  - Queue-agnostic structure for future Celery/RQ/Dramatiq integration
  - Reads shared environment settings (Redis, Postgres, poll interval)

- **postgres** (`PostgreSQL`)
  - Primary relational datastore
  - Persistent local volume configured

- **redis** (`Redis`)
  - Queue/cache backbone for async workloads
  - Persistent local volume configured

## Design Direction Support

This scaffold intentionally supports future architecture goals:

- Adapter-based ingestion from multiple MSP systems
- Canonical internal data model inside backend domain modules
- API + worker split for synchronous and asynchronous operations
- AI provider abstraction and privacy-first processing workflows
- Secure login/RBAC layers to be added in dedicated modules

## Runtime Topology

- Frontend exposed on `:5173`
- Backend exposed on `:8000`
- Postgres exposed on `:5432`
- Redis exposed on `:6379`
- Docker Compose orchestrates full stack startup
