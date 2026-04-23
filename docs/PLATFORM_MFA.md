# Platform operator MFA (TOTP)

This document describes **platform-administrator** multi-factor authentication in mspintel. **Tenant workspace users** do not use this flow; `/api/v1/auth/login` is unchanged.

## Goals

- Strengthen **platform console** sign-in with **TOTP** (RFC 6238) as the first MFA method.
- Keep a **clear extension path** for **WebAuthn** (`user_mfa_methods.method_type`, `method_metadata` JSON) without building WebAuthn in this phase.
- Avoid a full identity platform: short-lived **step JWTs**, one table for methods, Fernet encryption for TOTP shared secrets.

## Data model (`user_mfa_methods`)

| Column | Purpose |
| --- | --- |
| `user_id` | Owner (same `users` table as tenants; only **platform admins** use TOTP in this release). |
| `method_type` | e.g. `totp`; future: `webauthn`. |
| `is_enabled` | `false` while enrolling until the user proves possession with a valid code. |
| `ciphertext` | **Encrypted** TOTP shared secret (never store raw base32 in plaintext). |
| `method_label` | Human-readable label (default “Authenticator app”). |
| `method_metadata` | JSON for future WebAuthn credential descriptors, etc. |
| `verified_at` | Set when TOTP is confirmed and `is_enabled` becomes true. |

**Uniqueness:** `(user_id, method_type)` — one TOTP row per user.

## Recovery codes (`platform_mfa_recovery_codes`)

Platform admins with **enabled TOTP** may generate **one-time recovery codes** for MFA step-up when the authenticator is unavailable. **Tenant users** do not use this table.

| Column | Purpose |
| --- | --- |
| `user_id` | Owner (`users.id`). |
| `batch_id` | UUID grouping a single generation (regeneration deletes all **unused** rows for the user, then inserts a new batch). |
| `code_hash` | **HMAC-SHA256** digest of the normalized code using `MFA_RECOVERY_CODE_PEPPER` and `user_id` (see `platform_recovery_code_hash.py`). **Plaintext codes are never stored.** |
| `is_used` / `used_at` | One-time use: successful login sets `is_used` and timestamp. |

**Indexes:** `(user_id, is_used)` for counts; `(user_id, batch_id)` for housekeeping.

**Generation:** `POST /api/v1/platform/mfa/recovery-codes/generate` (full platform session). Returns **10** codes **once** in the JSON body; the server persists only hashes. Regenerating deletes unused codes from prior batches and emits `platform.mfa.recovery_codes.regenerated` instead of `...generated` when prior unused codes existed.

**Login:** `POST /api/v1/auth/platform/login/mfa` accepts **either** `totp_code` **or** `recovery_code` (mutually exclusive). On success, `platform.login` audit includes `via`: `totp` or `recovery_code`.

**Disable TOTP:** `POST /api/v1/platform/mfa/totp/disable` removes the TOTP row **and** all recovery-code rows for that user.

**Security note:** the pepper must be **long and random in production** (minimum 16 characters enforced at settings load). Database backup exposure still requires the pepper to compute guesses offline—rotate pepper only with a migration plan that re-hashes or invalidates codes.

## Encryption approach

- **Algorithm:** Fernet (symmetric authenticated encryption from the `cryptography` library).
- **Key:** `MFA_TOTP_ENCRYPTION_KEY` (settings / env). Must be a **strong random** 32-byte url-safe base64 key in production.
- **Payload:** JSON wrapper versioning the blob, e.g. `{"v":1,"k":"totp","s":"<base32 secret>"}` then Fernet-encrypted to the string stored in `ciphertext`.
- **Rationale:** Protects database backups and SQL dumps; defense-in-depth beside disk encryption.

## Policy: `PLATFORM_MFA_REQUIRED`

- **`false` (default):** Operators may sign in with password only if they have **not** enabled TOTP. If they **have** enabled TOTP, password login always returns **`mfa_challenge`** (no access/refresh tokens until TOTP succeeds).
- **`true`:** After a valid password, if the user has **no enabled TOTP**, the API returns **`mfa_enrollment_setup`** and an **`mfa_enroll`** step JWT (`enrollment_setup_token`). No platform session is issued until TOTP is enrolled **and** the subsequent **challenge** step completes.

Tenant login is **not** gated by this flag.

## Login and step tokens

1. **`POST /api/v1/auth/platform/login`** — email/password; response `PlatformLoginResponse` with `outcome`.
2. If **`mfa_challenge`:** client collects **TOTP** or a **recovery code** and calls **`POST /api/v1/auth/platform/login/mfa`** with `mfa_challenge_token` and **either** `totp_code` **or** `recovery_code` (not both). On success, normal **`TokenPairResponse`** is returned and **`platform.login`** is audited (`via: totp` or `via: recovery_code` in details).
3. If **`mfa_enrollment_setup`:** client uses `enrollment_setup_token` as **Bearer** only for **`POST /api/v1/platform/mfa/totp/enrollment`** and **`.../confirm`** (see `get_platform_mfa_actor`). After confirm, the user must complete **`mfa_challenge`** via another password login (or the UI may re-submit password once) and **`/platform/login/mfa`**.

Step tokens are JWTs signed with `jwt_secret_key`, with `typ` of `mfa_challenge` or `mfa_enroll`, and TTL from `MFA_CHALLENGE_TTL_MINUTES` / `MFA_ENROLLMENT_SETUP_TTL_MINUTES`.

**Important:** Access and refresh tokens are **not** issued until the flow reaches a normal token issuance path (password-only when MFA not required and no TOTP; or after successful **`/platform/login/mfa`** when TOTP is enabled).

## Enrolment (happy path)

1. Operator opens **`/platform/security`** (with a full platform session **or**, when policy requires MFA and they have no TOTP yet, after password using the setup token as Bearer).
2. **`POST /api/v1/platform/mfa/totp/enrollment`** — creates a **disabled** row, returns `method_id` + `otpauth_uri` (for QR / manual entry).
3. User enters a valid code → **`POST /api/v1/platform/mfa/totp/enrollment/confirm`** — sets `is_enabled`, `verified_at`, audits **`platform.mfa.enabled`**.
4. If TOTP was already required for login, the user completes **`/platform/login/mfa`** with a fresh challenge.

## Disable

- **`POST /api/v1/platform/mfa/totp/disable`** requires a **full platform access** token (not only the enrolment setup token) and a **valid current TOTP** code. Row is deleted; **`platform.mfa.disabled`** is audited.

## Audit events (`tenant_id = NULL`)

| Event | When |
| --- | --- |
| `platform.mfa.enrollment_started` | TOTP enrolment row created (pending). |
| `platform.mfa.enabled` | TOTP confirmed and enabled. |
| `platform.mfa.disabled` | TOTP removed after valid code. |
| `platform.mfa.challenge_issued` | Password ok, TOTP required for session. |
| `platform.mfa.challenge_passed` | TOTP verify succeeded on `/platform/login/mfa`. |
| `platform.mfa.challenge_failed` | Second factor failed; `details` includes `reason` (`invalid_totp` \| `invalid_recovery_code`) and `ip` when known — **never** raw TOTP or recovery values. |
| `platform.mfa.recovery_codes.generated` | New batch of recovery codes created (no unused codes invalidated). |
| `platform.mfa.recovery_codes.regenerated` | New batch created after deleting prior **unused** codes. |
| `platform.mfa.recovery_code.used` | A recovery code verified and consumed at login. |
| `platform.mfa.setup_token_issued` | Policy requires MFA, user has no TOTP yet — enrolment-only token returned. |
| `platform.login` | Full platform session issued (password-only or after MFA). |

Secrets and raw TOTP codes are **not** written to audit `details`.

## WebAuthn (future)

- Add rows with `method_type = 'webauthn'` and store credential metadata in `method_metadata` (and optionally `ciphertext` for opaque blobs).
- Reuse the same **`mfa_challenge`** pattern with a different verifier plugged into `PlatformMfaService`.
- Keep **platform-only** enforcement in `auth.py` / platform routers.

## Configuration (env)

See root **`.env.example`** and [docs/PLATFORM_AUTH_HARDENING.md](PLATFORM_AUTH_HARDENING.md):

- **TOTP / enrolment:** `PLATFORM_MFA_REQUIRED`, `MFA_TOTP_ENCRYPTION_KEY`, `MFA_CHALLENGE_TTL_MINUTES`, `MFA_ENROLLMENT_SETUP_TTL_MINUTES`.
- **Recovery codes:** `MFA_RECOVERY_CODE_PEPPER` (required length ≥ 16; use a strong secret in production).
- **Platform login rate limits:** `PLATFORM_LOGIN_RATELIMIT_ENABLED`, `PLATFORM_LOGIN_PASSWORD_*`, `PLATFORM_LOGIN_MFA_*`, `REDIS_URL`.

## Limitations (current release)

- Recovery codes are **platform-admin only**; no **tenant-user** MFA.
- No **WebAuthn** yet (extension point remains `user_mfa_methods`).
- Single **TOTP** method per user (`uq_user_mfa_method_type`).
- Rate limiting is **fixed-window / IP-oriented**; not a full account lockout product (see PLATFORM_AUTH_HARDENING.md).

`MFA_TOTP_ENCRYPTION_KEY` is validated at process startup (must be a valid Fernet key); misconfiguration fails fast so secrets are never written with a broken cipher.

## Migration

- Alembic **`0006_user_mfa_methods`** creates `user_mfa_methods`.
- Alembic **`0007_platform_mfa_recovery_codes`** creates `platform_mfa_recovery_codes`.
- Alembic **`0008_plat_mfa_rc_hash_ix`** adds index `(user_id, code_hash)` (revision id kept ≤32 chars for `alembic_version`).

## Operational recovery (summary)

- **Lost phone / TOTP:** use a **recovery code** at the MFA step, then enroll a new authenticator from `/platform/security` if desired.
- **Lost recovery codes:** **regenerate** from `/platform/security` while still signed in with TOTP. If locked out entirely, follow your **break-glass** runbook (bootstrap admin, controlled DB procedure)—see [docs/PLATFORM_AUTH_HARDENING.md](PLATFORM_AUTH_HARDENING.md).
