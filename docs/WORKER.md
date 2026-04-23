# Background worker

The `worker` service runs a lightweight polling loop (`WORKER_POLL_SECONDS`, default 5).

## Invitation expiry sweep

Each poll executes a Postgres `UPDATE` that marks **`pending`** invitations with `expires_at < NOW()` as **`expired`**. The operation is idempotent: accepted, revoked, or already-expired rows are untouched.

The canonical ORM implementation used in tests and callable from the backend package is `InvitationRepository.expire_pending_past_expiry()` in `backend/app/repositories/invitations.py`. Keep the worker SQL aligned if the schema or statuses change.

## Configuration

The worker reads the same `.env` as other services. Ensure **`DATABASE_URL`** (or the default embedded URL) points at the Compose Postgres service (`postgres:5432` inside the Docker network). Redis is configured for future jobs but is not required for the invitation sweep.

## Logs

Look for lines such as:

```text
invitation_sweep expired_rows=0
```

Non-zero counts mean pending invitations were expired on that run.
