# mspintel Architecture (SaaS Multi-tenant Scaffold)

## Initial Service Layout

- **frontend** (`React + TypeScript + Vite`)
  - Contains base state/provider structure for:
    - public pages
    - authenticated app pages
    - platform admin pages
    - tenant admin pages
    - onboarding pages
    - future tenant switcher UX

- **backend** (`FastAPI`)
  - App factory setup with versioned routers
  - API health routes and platform context probe route
  - Modular package structure for SaaS domain growth

- **worker** (`Python`)
  - Independent background service
  - Queue-framework-ready for Celery/RQ/Dramatiq expansion

- **postgres** (`PostgreSQL 16`)
  - Primary relational store
  - Bootstrap SQL initializes SaaS core tables

- **redis** (`Redis 7`)
  - Queue/cache support for async and transient state needs

## Why Docker-first

Docker Compose gives one-command startup, reproducible environments, and clean separation of services that mirrors production-oriented deployment style.

## SaaS Multi-tenant Concept Model

Initial conceptual model baked into schema and module layout:

- `users` = global identities
- `tenants` = MSP organizations/workspaces
- `tenant_memberships` = user-tenant role assignments
- `plans` = available subscription tiers
- `subscriptions` = tenant billing/subscription state
- platform admins are distinct from tenant admins

The scaffold shapes architecture around strict tenant-isolation checks and membership checks, while deferring full implementation detail to future iterations.

## Planned Backend / Frontend / Worker Split

- **Backend API**: identity, access, tenant context, orchestration, integration surfaces
- **Worker**: background ingestion, enrichment, notifications, and AI/batch jobs
- **Frontend**: public + authenticated SaaS UX layers and role-aware admin surfaces

## Future Adapter-based Model

Architecture supports future adapters for Autotask, ConnectWise, ITQuoter, Veeam, and additional systems by separating source adapter concerns from canonical internal models.
