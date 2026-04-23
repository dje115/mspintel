import uuid

from sqlalchemy import select

from app.models.entities import Tenant, UserSession
from tests.helpers import auth_headers, create_user_with_membership


def test_sessions_list_only_own_and_current_flag(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="s1", name="S1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "sess@example.com", "tenant_admin", tenant)

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "ChangeMe123!"}).json()
    sid = login["session_id"]
    headers = auth_headers(user, str(tenant.id), session_id=uuid.UUID(sid))

    res = client.get("/api/v1/auth/sessions", headers=headers)
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) >= 1
    assert sum(1 for r in rows if r["is_current"]) == 1


def test_revoke_other_session(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="s2", name="S2", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "sess2@example.com", "tenant_admin", tenant)

    a = client.post("/api/v1/auth/login", json={"email": user.email, "password": "ChangeMe123!"}).json()
    b = client.post("/api/v1/auth/login", json={"email": user.email, "password": "ChangeMe123!"}).json()

    headers_a = auth_headers(user, str(tenant.id), session_id=uuid.UUID(a["session_id"]))
    other_id = uuid.UUID(b["session_id"])

    revoke = client.post(f"/api/v1/auth/sessions/{other_id}/revoke", headers=headers_a)
    assert revoke.status_code == 200
    assert revoke.json()["revoked"] is True

    assert client.post("/api/v1/auth/refresh", json={"refresh_token": b["refresh_token"]}).status_code == 401


def test_cannot_revoke_current_session_via_api(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="s4", name="S4", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "sess4@example.com", "tenant_admin", tenant)

    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "ChangeMe123!"}).json()
    sid = uuid.UUID(login["session_id"])
    headers = auth_headers(user, str(tenant.id), session_id=sid)

    res = client.post(f"/api/v1/auth/sessions/{sid}/revoke", headers=headers)
    assert res.status_code == 400
    assert "logout" in res.json()["detail"].lower()


def test_repository_revoke_idempotent(db_session):
    from datetime import UTC, datetime, timedelta

    from app.repositories.sessions import SessionRepository

    tenant = Tenant(id=uuid.uuid4(), slug="s3", name="S3", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "sess3@example.com", "tenant_admin", tenant)

    s = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token_hash="abc",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(s)
    db_session.commit()

    repo = SessionRepository(db_session)
    row = db_session.scalars(select(UserSession).where(UserSession.id == s.id)).one()
    repo.revoke(row)
    db_session.refresh(row)
    assert row.revoked_at is not None
