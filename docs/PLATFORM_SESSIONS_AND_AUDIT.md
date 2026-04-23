# Platform sessions, token TTL, and audit

## Token lifetimes

JWT expiry is driven by **explicit settings** (see root `.env.example`):

| Setting | Purpose |
| --- | --- |
| `TENANT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL for tenant sessions (`am=tenant`) |
| `TENANT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL for tenant sessions |
| `PLATFORM_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL for platform console (`am=platform`) |
| `PLATFORM_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL for platform console |

Implementation: `app/core/token_policy.py` (`access_refresh_deltas`) is the single place that maps `auth_mode` → `(access_delta, refresh_delta)`. `AuthService.issue_token_pair` always uses it; `create_access_token` / `create_refresh_token` in `app/core/security.py` require an explicit `timedelta` (no hidden defaults).

## `user_sessions.auth_mode`

Migration `0005_platform_session_audit` adds `auth_mode` (`tenant` \| `platform`) so refresh rows match the JWT scope.

- **List sessions** (`GET /api/v1/auth/sessions`) returns only rows matching the caller’s JWT `am`.
- **Logout-all** revokes only rows matching that `auth_mode` (platform “sign out everywhere” does not revoke tenant refresh sessions for the same user, and vice versa).
- **Revoke** rejects revoking a session whose `auth_mode` differs from the caller’s token (403 with a clear message).

Legacy rows: migration backfills `tenant`.

## Audit: platform vs tenant

`audit_events.tenant_id` is **nullable**. Tenant-scoped events (memberships, invitations, tenant session revoke with tenant audit context) keep a real `tenant_id`.

Platform-scoped events use `tenant_id = NULL` and distinct `event_type` values, including:

| `event_type` | When |
| --- | --- |
| `platform.login` | Successful platform console sign-in |
| `platform.session.revoked` | Operator revoked another platform refresh session |
| `platform.sessions.logout_all` | Operator used logout-all from a platform session |
| `platform.login.rate_limited` | Platform password or MFA step exceeded configured Redis rate limit (`details.scope`: `password` \| `mfa`). |

MFA- and recovery-specific types (`platform.mfa.*`, `platform.login` after MFA) are listed in [docs/PLATFORM_MFA.md](PLATFORM_MFA.md).

Do not invent a synthetic “platform tenant” row: absence of `tenant_id` means **global / platform realm**.

## Future MFA / step-up

`app/services/platform_auth.py` defines `validate_platform_login_extras`, invoked from `POST /api/v1/auth/platform/login` **after** password verification and **before** token issuance. Extend that function (or replace it with a richer verifier) to add MFA without changing tenant `login` behaviour.
