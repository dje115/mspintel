"""Platform vs tenant session TTL, scoped logout/list/revoke, and platform audit rows."""

import uuid
from datetime import UTC, datetime

from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.core.security import get_password_hash
from app.models.entities import AuditEvent, Tenant, User
from tests.helpers import create_user_with_membership, platform_password_login


def _decode_exp(access_token: str) -> datetime:
    s = get_settings()
    payload = jose_jwt.decode(
        access_token, s.jwt_secret_key, algorithms=[s.jwt_algorithm], options={"verify_aud": False}
    )
    return datetime.fromtimestamp(int(payload["exp"]), tz=UTC)


def test_platform_access_token_expires_before_tenant(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ttl1", name="TTL1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    tu = create_user_with_membership(db_session, "ttl-tenant@example.com", "tenant_admin", tenant)
    pa = User(
        id=uuid.uuid4(),
        email="ttl-plat@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()

    tenant_pair = client.post(
        "/api/v1/auth/login", json={"email": tu.email, "password": "ChangeMe123!"}
    ).json()
    plat_pair = platform_password_login(client, pa.email, "ChangeMe123!")

    t_exp = _decode_exp(tenant_pair["access_token"])
    p_exp = _decode_exp(plat_pair["access_token"])
    assert p_exp < t_exp


def test_session_lists_are_scoped_by_auth_mode(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="ttl2", name="TTL2", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    tu = create_user_with_membership(db_session, "scope-tenant@example.com", "tenant_admin", tenant)
    pa = User(
        id=uuid.uuid4(),
        email="scope-plat@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()

    ten = client.post("/api/v1/auth/login", json={"email": tu.email, "password": "ChangeMe123!"}).json()
    platform_password_login(client, pa.email, "ChangeMe123!")
    p1 = platform_password_login(client, pa.email, "ChangeMe123!")
    platform_password_login(client, pa.email, "ChangeMe123!")

    t_headers = {"Authorization": f"Bearer {ten['access_token']}", "X-Tenant-Id": str(tenant.id)}
    tenant_rows = client.get("/api/v1/auth/sessions", headers=t_headers).json()
    assert len(tenant_rows) == 1
    assert tenant_rows[0]["auth_mode"] == "tenant"

    p_headers = {"Authorization": f"Bearer {p1['access_token']}"}
    plat_rows = client.get("/api/v1/auth/sessions", headers=p_headers).json()
    assert len(plat_rows) == 3
    assert all(r["auth_mode"] == "platform" for r in plat_rows)


def test_platform_revoke_other_session_ok(client, db_session: Session):
    pa = User(
        id=uuid.uuid4(),
        email="rev-plat@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()

    a = platform_password_login(client, pa.email, "ChangeMe123!")
    platform_password_login(client, pa.email, "ChangeMe123!")
    headers = {"Authorization": f"Bearer {a['access_token']}"}
    rows = client.get("/api/v1/auth/sessions", headers=headers).json()
    other = next(r for r in rows if not r["is_current"])

    res = client.post(f"/api/v1/auth/sessions/{other['id']}/revoke", headers=headers)
    assert res.status_code == 200
    assert res.json()["revoked"] is True


def test_platform_cannot_revoke_current_via_revoke_endpoint(client, db_session: Session):
    pa = User(
        id=uuid.uuid4(),
        email="cur-plat@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()
    a = platform_password_login(client, pa.email, "ChangeMe123!")
    sid = a["session_id"]
    headers = {"Authorization": f"Bearer {a['access_token']}"}
    res = client.post(f"/api/v1/auth/sessions/{sid}/revoke", headers=headers)
    assert res.status_code == 400


def test_platform_logout_all_keeps_current_refresh(client, db_session: Session):
    pa = User(
        id=uuid.uuid4(),
        email="lo-plat@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()
    p1 = platform_password_login(client, pa.email, "ChangeMe123!")
    p2 = platform_password_login(client, pa.email, "ChangeMe123!")
    headers = {"Authorization": f"Bearer {p2['access_token']}"}
    res = client.post(
        "/api/v1/auth/logout-all",
        headers=headers,
        json={"keep_refresh_token": p2["refresh_token"]},
    )
    assert res.status_code == 200
    assert res.json()["revoked_sessions"] == 1
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": p1["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": p2["refresh_token"]}).status_code == 200


def test_platform_login_writes_audit_row(client, db_session: Session):
    pa = User(
        id=uuid.uuid4(),
        email="aud-plat@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()
    platform_password_login(client, pa.email, "ChangeMe123!")
    db_session.expire_all()
    row = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.event_type == "platform.login",
            AuditEvent.tenant_id.is_(None),
            AuditEvent.actor_user_id == pa.id,
        )
    ).first()
    assert row is not None
    assert row.actor_user_id == pa.id


def test_platform_revoke_writes_platform_audit(client, db_session: Session):
    pa = User(
        id=uuid.uuid4(),
        email="aud-rev@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()
    a = platform_password_login(client, pa.email, "ChangeMe123!")
    platform_password_login(client, pa.email, "ChangeMe123!")
    headers = {"Authorization": f"Bearer {a['access_token']}"}
    rows = client.get("/api/v1/auth/sessions", headers=headers).json()
    other = next(r for r in rows if not r["is_current"])
    before = db_session.query(AuditEvent).count()
    client.post(f"/api/v1/auth/sessions/{other['id']}/revoke", headers=headers)
    after = db_session.query(AuditEvent).count()
    assert after > before
    db_session.expire_all()
    revoked_row = db_session.scalars(
        select(AuditEvent)
        .where(AuditEvent.event_type == "platform.session.revoked", AuditEvent.actor_user_id == pa.id)
        .order_by(AuditEvent.created_at.desc())
    ).first()
    assert revoked_row is not None
    assert revoked_row.tenant_id is None


def test_platform_logout_all_writes_audit(client, db_session: Session):
    pa = User(
        id=uuid.uuid4(),
        email="aud-lo@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()
    p = platform_password_login(client, pa.email, "ChangeMe123!")
    headers = {"Authorization": f"Bearer {p['access_token']}"}
    client.post("/api/v1/auth/logout-all", headers=headers, json={})
    db_session.expire_all()
    row = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.event_type == "platform.sessions.logout_all", AuditEvent.actor_user_id == pa.id
        )
    ).first()
    assert row is not None
    assert row.tenant_id is None


def test_tenant_cannot_revoke_platform_session_id(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="x1", name="X1", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    tu = create_user_with_membership(db_session, "x-tenant@example.com", "tenant_admin", tenant)
    pa = User(
        id=uuid.uuid4(),
        email="x-plat@example.com",
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(pa)
    db_session.commit()
    plat = platform_password_login(client, pa.email, "ChangeMe123!")
    plat_sid = plat["session_id"]
    ten = client.post("/api/v1/auth/login", json={"email": tu.email, "password": "ChangeMe123!"}).json()
    headers = {
        "Authorization": f"Bearer {ten['access_token']}",
        "X-Tenant-Id": str(tenant.id),
    }
    res = client.post(f"/api/v1/auth/sessions/{plat_sid}/revoke", headers=headers)
    assert res.status_code == 404
