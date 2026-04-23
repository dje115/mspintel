# Platform login hardening and abuse resistance

This document covers **platform-administrator** sign-in protections added alongside MFA recovery codes. **Tenant** `POST /api/v1/auth/login` is unchanged.

## Goals

- Reduce brute-force pressure on **`POST /api/v1/auth/platform/login`** (password step) and **`POST /api/v1/auth/platform/login/mfa`** (TOTP or recovery code).
- Use **Redis** for counters so limits survive process restarts in a typical deployment.
- **Fail open** when rate limiting is disabled or Redis is unavailable, so availability is not worse than before hardening (operators should still monitor Redis health).

## Mechanism: fixed-window counters

For each scope, failed attempts increment a Redis key with a TTL equal to the configured window. When the count **exceeds** the configured maximum, the API returns **HTTP 429** with a generic body and an audit event (see below). Successful login does **not** reset the window in this implementation (a deliberate simplicity trade-off; tune windows if needed).

| Scope | Redis key pattern | Counted when |
| --- | --- | --- |
| Password | `mspintel:rl:platform:pw:{ip-or-unknown}` | Wrong password, non-platform-admin attempting platform login, or `validate_platform_login_extras` failure after password verified (same generic handling as other failures where applicable). |
| MFA | `mspintel:rl:platform:mfa:{ip-or-unknown}:{user_id}` | Invalid TOTP or invalid / already-used recovery code on `/platform/login/mfa`. |

**IP source:** request client IP from middleware / connection (may be a proxy hop; align with your reverse proxy trusted headers in production).

## Configuration (environment)

| Variable | Default | Purpose |
| --- | --- | --- |
| `PLATFORM_LOGIN_RATELIMIT_ENABLED` | `true` | When `false`, no Redis client is used for these limits (always allow). Tests set this to `false` for determinism. |
| `PLATFORM_LOGIN_PASSWORD_MAX_ATTEMPTS` | `30` | Max failed password-step events per IP per window. |
| `PLATFORM_LOGIN_PASSWORD_WINDOW_SECONDS` | `900` | Window (15 minutes). |
| `PLATFORM_LOGIN_MFA_MAX_ATTEMPTS` | `40` | Max failed MFA attempts per IP **and** user id per window. |
| `PLATFORM_LOGIN_MFA_WINDOW_SECONDS` | `900` | Window (15 minutes). |

`REDIS_URL` must point at a reachable Redis when rate limiting is enabled.

## HTTP and information disclosure

- **429 responses** use a **generic** message (e.g. too many attempts). They do not distinguish TOTP vs recovery code vs “user exists”.
- **401** on platform login remains the usual **uniform** handling for bad credentials vs non-admin where that policy already applies—do not expand enumeration surface in new code paths.
- **401** on failed platform MFA step uses the same **`Unable to complete sign-in`** detail for invalid TOTP and invalid recovery codes (audit rows still carry a non-sensitive `reason` code).

## Audit events (`tenant_id = NULL`)

| `event_type` | When |
| --- | --- |
| `platform.login.rate_limited` | A request was rejected due to rate limiting. `details` includes `scope` (`password` or `mfa`) and `ip` where available—not raw secrets. |

See [docs/PLATFORM_MFA.md](PLATFORM_MFA.md) for MFA challenge audits (`platform.mfa.challenge_failed`, recovery-code events).

## Operational recovery (break-glass)

1. **Lost authenticator, recovery codes available:** sign in with password, then submit a **recovery code** instead of TOTP on the MFA step (see PLATFORM_MFA.md).
2. **Lost authenticator and lost recovery codes:** there is **no** undocumented API bypass. Use a controlled operational path:
   - **Bootstrap / seed platform admin** (development: `SEED_PLATFORM_ADMIN_*` in `.env`; production: provision at least one break-glass admin through your deployment runbook and protect those credentials and DB access).
   - **Database / support tooling:** a trusted operator with database access could reset MFA state **only** with explicit policy—this is outside the app’s normal UX and must be documented in your own security procedures.

Do not add silent “back doors” in application code without the same level of documentation and access control as above.

## Limitations (current release)

- Fixed-window only (no token bucket or sliding window).
- Keys are keyed by client IP (and user id for MFA); distributed attacks from many IPs are not mitigated here.
- No per-email counters (by design, to reduce account enumeration and implementation coupling).

## Future work

- Optional stricter policy (e.g. stricter windows in production only).
- **WebAuthn** as a second factor ([docs/PLATFORM_MFA.md](PLATFORM_MFA.md)) with the same Redis scopes extended if needed.
