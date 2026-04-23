import uuid

from app.models.entities import Tenant
from tests.helpers import auth_headers, create_user_with_membership


def test_refresh_and_logout_revokes_previous_session(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="auth", name="Auth", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "auth-user@example.com", "tenant_admin", tenant)

    login_res = client.post(
        "/api/v1/auth/login", json={"email": "auth-user@example.com", "password": "ChangeMe123!"}
    )
    assert login_res.status_code == 200
    token_pair = login_res.json()
    assert "session_id" in token_pair

    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": token_pair["refresh_token"]})
    assert refresh_res.status_code == 200
    rotated_pair = refresh_res.json()
    assert rotated_pair["refresh_token"] != token_pair["refresh_token"]

    old_refresh_again = client.post("/api/v1/auth/refresh", json={"refresh_token": token_pair["refresh_token"]})
    assert old_refresh_again.status_code == 401

    logout_res = client.post("/api/v1/auth/logout", json={"refresh_token": rotated_pair["refresh_token"]})
    assert logout_res.status_code == 200

    revoked_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": rotated_pair["refresh_token"]})
    assert revoked_refresh.status_code == 401


def test_logout_all_revokes_all_sessions(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="auth2", name="Auth2", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "logout-all@example.com", "tenant_admin", tenant)

    pair1 = client.post("/api/v1/auth/login", json={"email": user.email, "password": "ChangeMe123!"}).json()
    pair2 = client.post("/api/v1/auth/login", json={"email": user.email, "password": "ChangeMe123!"}).json()

    headers = auth_headers(user, str(tenant.id))
    logout_all = client.post("/api/v1/auth/logout-all", headers=headers)
    assert logout_all.status_code == 200

    assert client.post("/api/v1/auth/refresh", json={"refresh_token": pair1["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": pair2["refresh_token"]}).status_code == 401


def test_logout_all_keep_current_refresh(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="auth3", name="Auth3", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "logout-keep@example.com", "tenant_admin", tenant)

    pair1 = client.post("/api/v1/auth/login", json={"email": user.email, "password": "ChangeMe123!"}).json()
    pair2 = client.post("/api/v1/auth/login", json={"email": user.email, "password": "ChangeMe123!"}).json()

    headers2 = auth_headers(user, str(tenant.id), session_id=uuid.UUID(pair2["session_id"]))
    logout_all = client.post(
        "/api/v1/auth/logout-all",
        headers=headers2,
        json={"keep_refresh_token": pair2["refresh_token"]},
    )
    assert logout_all.status_code == 200
    assert logout_all.json()["revoked_sessions"] == 1

    assert client.post("/api/v1/auth/refresh", json={"refresh_token": pair1["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": pair2["refresh_token"]}).status_code == 200


def test_logout_all_rejects_invalid_json(client, db_session):
    tenant = Tenant(id=uuid.uuid4(), slug="auth4", name="Auth4", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    user = create_user_with_membership(db_session, "bad-json@example.com", "tenant_admin", tenant)

    headers = auth_headers(user, str(tenant.id))
    res = client.post(
        "/api/v1/auth/logout-all",
        headers={**headers, "Content-Type": "application/json"},
        content=b"{not json",
    )
    assert res.status_code == 400
