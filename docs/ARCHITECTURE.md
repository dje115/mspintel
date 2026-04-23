# Architecture

## v1.1 Focus

This phase hardens the SaaS access-control core before deeper analytics/connectors/billing integrations.

## Services

- `frontend`: public auth pages + protected tenant app pages
- `backend`: FastAPI API, access context, invitation/session logic
- `worker`: async job scaffold
- `postgres`: transactional store
- `redis`: cache/queue backbone
- `mailpit`: development SMTP and mail inbox

## Core Data Model

- `users`
- `tenants`
- `tenant_memberships`
- `tenant_invitations`
- `user_sessions`
- `plans`, `subscriptions`
- `audit_events`

## Access Context and Permissions

- Access context resolves authenticated user + selected tenant + effective membership role.
- Capabilities enforced with reusable server-side dependencies.
- Tenant admin member/invitation operations are tenant-bound and role-protected.
- Platform admins can be granted broader capabilities where explicitly intended.

## Invitation Security Model

- Invite tokens are generated server-side and sent via email.
- Response payloads include safe acceptance metadata; raw token exposure is disabled by default outside debug mode.
- Existing-account acceptance requires authentication as the invited email identity.
- Invite lifecycle statuses are constrained and tenant-scoped.

## Session Security Model

- Short-lived access tokens.
- Refresh sessions stored in `user_sessions` with hash + expiry + revocation timestamp.
- Refresh rotates session (old refresh token is invalidated).
- Logout revokes one session; logout-all revokes all sessions.

## Tenant Isolation

- Tenant-aware dependencies + membership checks on protected endpoints.
- Repository/service patterns keep tenant filtering the default.
- Cross-tenant reads/writes are denied unless explicitly intended.

## Versioning Strategy

- Runtime version is controlled by `MSPINTEL_APP_VERSION` (currently `1.1`).
- Compose maps `MSPINTEL_APP_VERSION` into backend and `VITE_MSPINTEL_APP_VERSION` into frontend.
- Future platform releases increment to `1.2`, `1.3`, etc by updating env/version references.
