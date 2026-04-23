"""Platform TOTP MFA: policy, login challenge, enrollment, audits (tenant_id NULL).

Deterministic: fixed passwords, pyotp against ``otpauth_uri`` secrets, no wall-clock sleeps
(TOTP ``valid_window`` on the server covers small skew).
"""

import json
import uuid
from urllib.parse import parse_qs, urlparse

import pyotp
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import settings as settings_module
from app.core.security import get_password_hash
from app.models.entities import AuditEvent, Tenant, User, UserMfaMethod, UserSession
from tests.helpers import create_user_with_membership, platform_password_login


@pytest.fixture
def platform_mfa_required_on(monkeypatch):
    settings_module.get_settings.cache_clear()
    monkeypatch.setenv("PLATFORM_MFA_REQUIRED", "true")
    yield
    settings_module.get_settings.cache_clear()
    monkeypatch.delenv("PLATFORM_MFA_REQUIRED", raising=False)


def make_platform_admin(db_session: Session, email: str) -> User:
    u = User(
        id=uuid.uuid4(),
        email=email,
        full_name="Plat",
        password_hash=get_password_hash("ChangeMe123!"),
        is_platform_admin=True,
    )
    db_session.add(u)
    db_session.commit()
    return u


def totp_secret_from_otpauth_uri(uri: str) -> str:
    """Parse ``secret`` query param from ``otpauth://`` URI (matches authenticator behaviour)."""
    return parse_qs(urlparse(uri).query)["secret"][0]


def post_totp_enrollment_start(client, bearer: str) -> dict:
    r = client.post(
        "/api/v1/platform/mfa/totp/enrollment",
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def post_totp_enrollment_confirm(client, bearer: str, method_id, code: str):
    return client.post(
        "/api/v1/platform/mfa/totp/enrollment/confirm",
        headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
        json={"method_id": str(method_id), "totp_code": code},
    )


def enable_totp_for_platform_user(client, db_session: Session, user: User) -> str:
    """Create and confirm TOTP; returns shared secret (policy off: password login yields tokens first)."""
    pair = platform_password_login(client, user.email, "ChangeMe123!")
    start = post_totp_enrollment_start(client, pair["access_token"])
    secret = totp_secret_from_otpauth_uri(start["otpauth_uri"])
    code = pyotp.TOTP(secret).now()
    r = post_totp_enrollment_confirm(client, pair["access_token"], start["method_id"], code)
    assert r.status_code == 200, r.text
    return secret


def post_platform_login_expect_challenge(client, email: str, password: str) -> dict:
    r = client.post("/api/v1/auth/platform/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"] == "mfa_challenge"
    return body


def complete_platform_login_with_totp(client, email: str, password: str, secret: str) -> dict:
    step1 = post_platform_login_expect_challenge(client, email, password)
    code = pyotp.TOTP(secret).now()
    r = client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step1["mfa_challenge_token"], "totp_code": code},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_platform_login_no_mfa_when_policy_allows(client, db_session: Session):
    u = make_platform_admin(db_session, "mfa-off@example.com")
    body = platform_password_login(client, u.email, "ChangeMe123!")
    assert body["access_token"]
    assert body["refresh_token"]


def testpost_platform_login_expect_challenge_when_totp_enabled_no_access_token(client, db_session: Session):
    u = make_platform_admin(db_session, "mfa-chal@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    assert secret

    body = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    assert not body.get("access_token")
    assert body.get("mfa_challenge_token")


def test_platform_login_mfa_invalid_code_rejected_and_audited(client, db_session: Session):
    u = make_platform_admin(db_session, "mfa-bad@example.com")
    enable_totp_for_platform_user(client, db_session, u)
    step1 = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    r = client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step1["mfa_challenge_token"], "totp_code": "000000"},
    )
    assert r.status_code == 401
    assert r.json().get("detail") == "Unable to complete sign-in"

    db_session.expire_all()
    row = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.event_type == "platform.mfa.challenge_failed", AuditEvent.actor_user_id == u.id
        )
    ).first()
    assert row is not None
    assert row.tenant_id is None
    assert json.loads(row.details or "{}").get("reason") == "invalid_totp"


def test_platform_login_mfa_valid_code_issues_tokens_and_audits(client, db_session: Session):
    u = make_platform_admin(db_session, "mfa-ok@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    pair = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    assert pair["access_token"]

    db_session.expire_all()
    passed = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.event_type == "platform.mfa.challenge_passed", AuditEvent.actor_user_id == u.id
        )
    ).first()
    assert passed is not None

    logins = db_session.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "platform.login", AuditEvent.actor_user_id == u.id)
    ).all()
    assert logins
    assert any(json.loads(x.details or "{}").get("via") == "totp" for x in logins)


def test_totp_enrollment_not_enabled_until_valid_confirm(client, db_session: Session):
    u = make_platform_admin(db_session, "mfa-pend@example.com")
    pair = platform_password_login(client, u.email, "ChangeMe123!")
    start = post_totp_enrollment_start(client, pair["access_token"])
    mid = uuid.UUID(str(start["method_id"]))
    secret = totp_secret_from_otpauth_uri(start["otpauth_uri"])

    row = db_session.get(UserMfaMethod, mid)
    assert row is not None
    assert row.is_enabled is False

    bad = post_totp_enrollment_confirm(client, pair["access_token"], mid, "000000")
    assert bad.status_code == 400
    db_session.expire_all()
    row = db_session.get(UserMfaMethod, mid)
    assert row is not None
    assert row.is_enabled is False

    code = pyotp.TOTP(secret).now()
    ok = post_totp_enrollment_confirm(client, pair["access_token"], mid, code)
    assert ok.status_code == 200
    db_session.expire_all()
    row = db_session.get(UserMfaMethod, mid)
    assert row is not None
    assert row.is_enabled is True

    enabled_audit = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.event_type == "platform.mfa.enabled", AuditEvent.actor_user_id == u.id
        )
    ).first()
    assert enabled_audit is not None


def test_password_step_does_not_create_session_before_mfa(client, db_session: Session):
    u = make_platform_admin(db_session, "mfa-sess@example.com")
    enable_totp_for_platform_user(client, db_session, u)
    before = len(db_session.scalars(select(UserSession).where(UserSession.user_id == u.id)).all())
    post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    after = len(db_session.scalars(select(UserSession).where(UserSession.user_id == u.id)).all())
    assert after == before


def test_platform_mfa_required_enrollment_setup_then_challenge(client, db_session: Session, platform_mfa_required_on):
    u = make_platform_admin(db_session, "mfa-req@example.com")
    r = client.post("/api/v1/auth/platform/login", json={"email": u.email, "password": "ChangeMe123!"})
    assert r.status_code == 200
    b = r.json()
    assert b["outcome"] == "mfa_enrollment_setup"
    assert b.get("enrollment_setup_token")
    assert not b.get("access_token")

    st = post_totp_enrollment_start(client, b["enrollment_setup_token"])
    secret = totp_secret_from_otpauth_uri(st["otpauth_uri"])
    code = pyotp.TOTP(secret).now()
    conf = post_totp_enrollment_confirm(client, b["enrollment_setup_token"], st["method_id"], code)
    assert conf.status_code == 200

    step1 = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    code2 = pyotp.TOTP(secret).now()
    pair = client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step1["mfa_challenge_token"], "totp_code": code2},
    ).json()
    assert pair["access_token"]


def test_tenant_login_unchanged_json_shape(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="mfad", name="MFAD", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    tu = create_user_with_membership(db_session, "mfa-tenant@example.com", "tenant_admin", tenant)
    r = client.post("/api/v1/auth/login", json={"email": tu.email, "password": "ChangeMe123!"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert "outcome" not in body


def test_mfa_enrollment_started_and_enabled_audits(client, db_session: Session):
    u = make_platform_admin(db_session, "mfa-aud@example.com")
    pair = platform_password_login(client, u.email, "ChangeMe123!")
    post_totp_enrollment_start(client, pair["access_token"])
    db_session.expire_all()
    started = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.event_type == "platform.mfa.enrollment_started", AuditEvent.actor_user_id == u.id
        )
    ).first()
    assert started is not None
    assert started.tenant_id is None


def test_disable_totp_with_valid_code(client, db_session: Session):
    u = make_platform_admin(db_session, "mfa-dis@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    pair = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    bad = client.post(
        "/api/v1/platform/mfa/totp/disable",
        headers={"Authorization": f"Bearer {pair['access_token']}", "Content-Type": "application/json"},
        json={"totp_code": "000000"},
    )
    assert bad.status_code == 400

    code = pyotp.TOTP(secret).now()
    ok = client.post(
        "/api/v1/platform/mfa/totp/disable",
        headers={"Authorization": f"Bearer {pair['access_token']}", "Content-Type": "application/json"},
        json={"totp_code": code},
    )
    assert ok.status_code == 200

    db_session.expire_all()
    row = db_session.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "platform.mfa.disabled", AuditEvent.actor_user_id == u.id)
    ).first()
    assert row is not None

    body = platform_password_login(client, u.email, "ChangeMe123!")
    assert body["outcome"] == "authenticated"


def test_mfa_totp_encryption_key_must_be_valid_fernet(monkeypatch):
    from pydantic import ValidationError

    from app.core.settings import Settings

    monkeypatch.setenv("MFA_TOTP_ENCRYPTION_KEY", "not-a-valid-fernet-key")
    with pytest.raises(ValidationError) as excinfo:
        Settings()
    err = str(excinfo.value).lower()
    assert "fernet" in err or "mfa_totp_encryption_key" in err
