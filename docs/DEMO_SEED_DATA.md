# Demo MSP seed data (`demo-msp`)

Synthetic, **tenant-scoped** data for the **`demo-msp`** workspace. All companies, people, and situations are **fictional** (UK-style names and industries for realism). Nothing is copied from real customers.

## What gets replaced

On every `seed_all` run (`python -m app.db.seed` or Docker entrypoint seed), for **`tenants.slug = demo-msp`** only:

- **Deleted** for that tenant: customers, contacts, tickets, opportunities, quotes, account scores, recommendations, actions, `ai_task_runs`, `source_entity_mappings`, `integration_sync_runs`, `source_system_connections` (canonical **`finance_*`** rows cascade with customers).
- **Recreated**: multi-connector **simulation** rows (Autotask, ConnectWise label, ITQuoter, Veeam, Microsoft 365, Xero, Sage), **31 customers**, related PSA-style entities, per-customer **`demo_profile`** JSON (billing / M365 / backup / relationship / data-quality narratives), and **canonical finance** rows (`finance_billing_accounts`, `finance_billing_snapshots`, `finance_invoices`) materialised from each profile. The seeded **Xero** connection stores `demo_mode: true` so **Integrations → Sync** can refresh the same canonical slice without live Xero API calls.

**Not** wiped: users, memberships, plans, subscriptions, onboarding state, AI providers (a default OpenAI row is ensured if missing), prompt definitions, tenant AI routes.

Other tenants are untouched.

## Record counts (order of magnitude)

| Area | Approximate count |
|------|-------------------|
| Customers | 31 |
| Source connections | 7 (simulated vendors) |
| Integration sync runs | 7 (one per connection, succeeded) |
| Source entity mappings | 31+ (PSA customer id ↔ canonical customer) |
| Contacts | 40+ |
| Tickets | 35+ |
| Opportunities | 20+ |
| Quotes | 15+ |
| Recommendations | 40+ |
| Actions | 15+ |
| Account scores | 31 |

Exact counts may drift slightly if `ACCOUNT_SPECS` in `backend/app/services/demo_rich_seed.py` change.

## `demo_profile` JSON (per customer)

Nullable column `customers.demo_profile`. For seeded accounts it includes:

- `synthetic`, `uk_demo`, `industry`, `city_line`, `scenario_note`
- **`billing`**: simulated Xero/Sage-style fields (seat/storage counts, aged debt GBP, invoice friction enum)
- **`microsoft_365`**: licensed users, active sign-ins, MFA %, unused licences, hygiene text
- **`backup`**: protected vs billed TB, failed jobs (7d), days since restore test
- **`relationship`**: days since strategic touch, stakeholder count, last QBR, notes
- **`data_quality`**: missing_fields list, confidence, optional `conflicts` for testing “cannot conclude” paths

Exposed on **`GET /api/v1/customers/{id}`** as `demo_profile` and rendered on Customer 360 when `synthetic` is true. Fed into **AI variable maps** under `customer.demo_profile` for richer prompts.

## Credentials (unchanged)

| Role | Email | Password |
|------|-------|----------|
| Tenant admin | `tenant-admin@demo-msp.example.com` | `ChangeMe123!` |
| Sales | `sales@demo-msp.example.com` | `ChangeMe123!` |
| Service manager | `service@demo-msp.example.com` | `ChangeMe123!` |

Platform admin: see root **README** seed table (`SEED_PLATFORM_ADMIN_*` env).

## Reseed / reset

1. **Full DB reset** (wiping all tenants): `docker compose down -v` then `docker compose up --build -d` (destructive).
2. **Reseed only** (keeps DB, reapplies seed including demo workspace replace):  
   `docker compose exec backend python -m app.db.seed`

Requires migration **`0012_customer_demo_profile`** applied (`alembic upgrade head` — normally automatic on backend container start).

## Assumptions

- **No live Autotask/Xero/M365 APIs** are called during seed; connector rows are **placeholders** with healthy `last_successful_sync_at` for UI/testing.
- Real connector sync remains a **separate** path (e.g. Autotask adapter tests in `backend/tests/test_integrations_connectors.py`).

See also: **[IMPLEMENTATION_STATUS_REVIEW.md](IMPLEMENTATION_STATUS_REVIEW.md)** for what in the product is real vs placeholder vs spec-only.
