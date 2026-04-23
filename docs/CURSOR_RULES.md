# Cursor / implementation rules (mspintel)

Standing rules for this repository. **Follow this document** for implementation work instead of re-stating the same constraints in every prompt.

---

## 1. Docker-first

- **mspintel is Docker-first.** Local and CI workflows should assume Compose is the primary way to run Postgres, Redis, backend, worker, frontend, and Mailpit together.
- **Every change** to code, runtime, dependencies, or configuration must keep **Dockerfiles**, **`compose.yaml`**, **`.env` / `.env.example` wiring**, and **container startup** (e.g. backend `docker-entrypoint.sh`, `alembic upgrade head`) **aligned**.
- If a feature needs a **new service** (queue, extra worker, sidecar, etc.), **add it to Compose** (and document ports/env) rather than relying on undocumented manual processes.
- After meaningful infra or dependency changes, **validate**: `docker compose config` and `docker compose up --build -d` (or equivalent) so the stack **builds and starts** cleanly.

---

## 2. Versioning

- When **platform / runtime / Docker** surface changes (or a release-worthy feature slice ships), **bump the central app version** (`MSPINTEL_APP_VERSION` / backend `app_version`, `VITE_APP_VERSION`, `compose.yaml` defaults, `frontend/package.json` where applicable).
- Keep the **version visible** on required surfaces (tenant login/signup, platform login/console pattern, tenant app shell as per current product layout).
- Keep **backend, frontend, Compose, and docs** version mentions **aligned** so operators are not misled.

---

## 3. Environment and configuration

- Whenever **environment variables** or **settings** change, **update root `.env.example`** with sensible defaults or placeholders and short comments where non-obvious.
- **Document new required config** in README and/or focused docs (e.g. security/MFA docs) so first-time and production setup stay reproducible.

---

## 4. Validation

After every **meaningful phase** (not necessarily every one-line typo fix):

- Run **appropriate checks**: e.g. `cd backend && python -m pytest`, `cd backend && python -m alembic heads` / `upgrade head` when migrations exist, `cd frontend && npm run build` (and `npm run lint` when touching TS/React).
- **Confirm Docker alignment** (`docker compose config`, and stack up when Dockerfiles or Compose change).
- **Confirm migrations** when the schema changes (Alembic revision chain, `down_revision`, and ≤32-char revision ids for `alembic_version` if applicable).
- **Confirm builds** for frontend and backend when those trees change.

---

## 5. Documentation

- Update **README** and/or **docs/** when **routes**, **auth flows**, **setup steps**, **env vars**, or **major behaviour** changes.
- Prefer linking to focused docs (e.g. `docs/PLATFORM_MFA.md`, `docs/TENANT_PRODUCT_WIREFRAMES.md`, `docs/ROUTES_UX_MAP.md`) from README instead of duplicating long prose.

---

## 6. GitHub (commit and push)

- **Commit and push only after validation** for the phase is complete (tests/builds/Docker as applicable).
- Use a **clear, conventional commit message** (imperative mood, scope when helpful). When reporting to the user, **state the exact commit message** used.

---

## 7. Reporting (end of each phase)

At the end of a phase, summarise for the user:

| Item | Content |
|------|---------|
| **What changed** | High-level list (features, fixes, files/areas). |
| **Commands to run** | e.g. migrations, tests, `docker compose up`, frontend build. |
| **URLs / routes affected** | New or changed paths in the SPA or API. |
| **Credentials** | If dev **seed** credentials or demo logins are relevant, repeat them or point to README. |
| **Docker** | Whether Dockerfiles/Compose/env were updated and whether the stack was validated. |
| **GitHub** | Whether changes were **pushed** (and to which branch if not `main`). |

---

## 8. Product UX

- The **tenant-facing MSP product** (`/login`, `/signup`, `/app/...`) is the **hero experience** — prefer polish, IA, and design-system consistency there.
- The **platform console** (`/platform/...`) should remain **visually and tonally distinct** (operational / operator tooling, not a clone of the tenant marketing shell).
- Keep **responsive** behaviour in mind for tenant layouts (sidebar collapse, tables, auth cards on smaller viewports).

---

## Stale frontend UI (Docker + Vite)

If the browser still shows an **old layout** (e.g. flat “Customers / Members” nav instead of grouped **Dashboard / Accounts & customers**), the dev server is usually serving a **stale bundle**:

1. **Pull latest** (`git pull`) and confirm `frontend/src/layout/AppLayout.tsx` uses `tenant-shell` / grouped nav.
2. **Restart the frontend container** after pulling: `docker compose restart frontend` (or `docker compose up --build -d`).
3. **Hard refresh** the browser (`Ctrl+Shift+R`) or use a private window.

Compose sets **`CHOKIDAR_USEPOLLING=true`** for the frontend service so Vite **polls** the bind-mounted `./frontend` tree (needed on many **Windows + Docker Desktop** setups where file events do not reach the container). Local `npm run dev` without Docker does not need this unless you see the same symptom.

---

## Quick reference commands

| Goal | Command |
|------|---------|
| Compose sanity | `docker compose config` |
| Stack up | `docker compose up --build -d` |
| DB migrations (container) | `docker compose exec backend alembic upgrade head` |
| Seed demo data | `docker compose exec backend python -m app.db.seed` |
| Backend tests | `cd backend && python -m pytest` |
| Frontend build | `cd frontend && npm run build` |

---

## Related docs

- [DEVELOPMENT.md](DEVELOPMENT.md) — local prerequisites, Compose quick start, tests.
- [README.md](../README.md) — overview, URLs, endpoints, seed credentials table.
- [ROUTES_UX_MAP.md](ROUTES_UX_MAP.md) — SPA routes and layouts.
- [TENANT_PRODUCT_WIREFRAMES.md](TENANT_PRODUCT_WIREFRAMES.md) — tenant product IA.
