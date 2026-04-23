"""Platform MFA recovery codes and platform-login rate limiting.

Deterministic: rate limiting is disabled via autouse ``conftest`` fixture; tests that need
the 429 path monkeypatch ``PLATFORM_LOGIN_RATELIMIT_ENABLED`` and stub Redis increment.
"""

import json
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import settings as settings_module
from app.core.security import get_password_hash
from app.models.entities import AuditEvent, PlatformMfaRecoveryCode, Tenant, UserSession
from app.services.platform_mfa import PlatformMfaService
from app.services.platform_recovery_code_hash import hash_platform_recovery_code
from tests.helpers import create_user_with_membership, platform_password_login
from tests.test_platform_mfa import (
    complete_platform_login_with_totp,
    enable_totp_for_platform_user,
    make_platform_admin,
    post_platform_login_expect_challenge,
)


def test_recovery_codes_stored_hashed_not_plaintext(client, db_session: Session):
    u = make_platform_admin(db_session, "rc-hash@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    pair = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    gen = client.post(
        "/api/v1/platform/mfa/recovery-codes/generate",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert gen.status_code == 200, gen.text
    codes = gen.json()["codes"]
    assert len(codes) == 10
    for c in codes:
        assert "-" in c
        assert c.upper() == c
    db_session.expire_all()
    rows = db_session.scalars(select(PlatformMfaRecoveryCode).where(PlatformMfaRecoveryCode.user_id == u.id)).all()
    assert len(rows) == 10
    for row in rows:
        assert row.code_hash
        assert len(row.code_hash) == 64  # SHA-256 hex from HMAC
        assert row.code_hash not in codes
        assert all(row.code_hash != c.replace("-", "") for c in codes)


def test_recovery_code_mfa_substitute_single_use(client, db_session: Session):
    u = make_platform_admin(db_session, "rc-use@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    pair = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    gen = client.post(
        "/api/v1/platform/mfa/recovery-codes/generate",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    code = gen.json()["codes"][0]

    step = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    r1 = client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step["mfa_challenge_token"], "recovery_code": code},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["access_token"]

    step2 = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    r2 = client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step2["mfa_challenge_token"], "recovery_code": code},
    )
    assert r2.status_code == 401

    db_session.expire_all()
    used = db_session.scalars(
        select(PlatformMfaRecoveryCode).where(PlatformMfaRecoveryCode.user_id == u.id, PlatformMfaRecoveryCode.is_used.is_(True))
    ).all()
    assert len(used) == 1


def test_regenerate_recovery_invalidates_unused(client, db_session: Session):
    u = make_platform_admin(db_session, "rc-regen@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    pair = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    g1 = client.post(
        "/api/v1/platform/mfa/recovery-codes/generate",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    ).json()
    old_code = g1["codes"][0]
    client.post(
        "/api/v1/platform/mfa/recovery-codes/generate",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    db_session.expire_all()
    pepper = settings_module.get_settings().mfa_recovery_code_pepper
    norm = old_code.replace("-", "").upper()
    digest = hash_platform_recovery_code(pepper, u.id, norm)
    row = db_session.scalars(
        select(PlatformMfaRecoveryCode).where(PlatformMfaRecoveryCode.user_id == u.id, PlatformMfaRecoveryCode.code_hash == digest)
    ).first()
    assert row is None

    st = client.get("/api/v1/platform/mfa/status", headers={"Authorization": f"Bearer {pair['access_token']}"}).json()
    assert st["recovery_codes_unused"] == 10

    regen = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.event_type == "platform.mfa.recovery_codes.regenerated", AuditEvent.actor_user_id == u.id
        )
    ).first()
    assert regen is not None


def test_recovery_audit_used_event(client, db_session: Session):
    u = make_platform_admin(db_session, "rc-audit@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    pair = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    code = client.post(
        "/api/v1/platform/mfa/recovery-codes/generate",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    ).json()["codes"][0]
    step = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step["mfa_challenge_token"], "recovery_code": code},
    )
    db_session.expire_all()
    ev = db_session.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "platform.mfa.recovery_code.used", AuditEvent.actor_user_id == u.id)
    ).first()
    assert ev is not None
    assert ev.tenant_id is None


def test_no_session_before_recovery_mfa_passes(client, db_session: Session):
    u = make_platform_admin(db_session, "rc-sess@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    db_session.refresh(u)
    codes, _ = PlatformMfaService(db_session).generate_recovery_codes(u, ip=None)
    code = codes[0]

    before = len(db_session.scalars(select(UserSession).where(UserSession.user_id == u.id)).all())
    step = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    after_challenge = len(db_session.scalars(select(UserSession).where(UserSession.user_id == u.id)).all())
    assert after_challenge == before

    client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step["mfa_challenge_token"], "recovery_code": code},
    )
    after = len(db_session.scalars(select(UserSession).where(UserSession.user_id == u.id)).all())
    assert after == before + 1


def test_invalid_recovery_code_challenge_failed_audit(client, db_session: Session):
    u = make_platform_admin(db_session, "rc-bad@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    pair = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    client.post(
        "/api/v1/platform/mfa/recovery-codes/generate",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    step = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    r = client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step["mfa_challenge_token"], "recovery_code": "AAAAA-BBBBB"},
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
    assert json.loads(row.details or "{}").get("reason") == "invalid_recovery_code"


def test_tenant_login_unaffected_by_platform_recovery(client, db_session: Session):
    tenant = Tenant(id=uuid.uuid4(), slug="rc-t", name="RC", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    tu = create_user_with_membership(db_session, "rc-tenant@example.com", "tenant_admin", tenant)
    r = client.post("/api/v1/auth/login", json={"email": tu.email, "password": "ChangeMe123!"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_platform_password_rate_limit_returns_429(monkeypatch, client, db_session: Session):
    monkeypatch.setenv("PLATFORM_LOGIN_RATELIMIT_ENABLED", "true")
    settings_module.get_settings.cache_clear()
    from app.services import platform_login_ratelimit as rl

    monkeypatch.setattr(rl, "_incr_limited", lambda *a, **k: False)
    r = client.post("/api/v1/auth/platform/login", json={"email": "nope@example.com", "password": "wrong"})
    assert r.status_code == 429
    settings_module.get_settings.cache_clear()


def test_platform_mfa_rate_limit_returns_429(monkeypatch, client, db_session: Session):
    u = make_platform_admin(db_session, "rl-mfa@example.com")
    enable_totp_for_platform_user(client, db_session, u)
    monkeypatch.setenv("PLATFORM_LOGIN_RATELIMIT_ENABLED", "true")
    settings_module.get_settings.cache_clear()
    from app.services import platform_login_ratelimit as rl

    monkeypatch.setattr(rl, "_incr_limited", lambda *a, **k: False)
    step = post_platform_login_expect_challenge(client, u.email, "ChangeMe123!")
    r = client.post(
        "/api/v1/auth/platform/login/mfa",
        json={"mfa_challenge_token": step["mfa_challenge_token"], "totp_code": "000000"},
    )
    assert r.status_code == 429
    settings_module.get_settings.cache_clear()


def test_totp_still_works_after_recovery_generate(client, db_session: Session):
    u = make_platform_admin(db_session, "rc-totp@example.com")
    secret = enable_totp_for_platform_user(client, db_session, u)
    pair = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    client.post(
        "/api/v1/platform/mfa/recovery-codes/generate",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    out = complete_platform_login_with_totp(client, u.email, "ChangeMe123!", secret)
    assert out["access_token"]
