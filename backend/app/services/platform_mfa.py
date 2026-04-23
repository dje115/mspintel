"""Platform-operator TOTP MFA (enrolment, verification, disable).

WebAuthn: store credential payloads in ``UserMfaMethod.method_metadata`` and use
``method_type == \"webauthn\"`` when implemented; keep ``ciphertext`` for encrypted blobs
or empty where metadata alone suffices (product choice at WebAuthn time).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

import pyotp
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import User, UserMfaMethod
from app.services.audit import AuditService
from app.services.mfa_totp_crypto import get_totp_secret_crypto

MFA_METHOD_TOTP = "totp"


class PlatformMfaService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    def has_enabled_totp(self, user_id: UUID) -> bool:
        row = self.db.scalars(
            select(UserMfaMethod).where(
                UserMfaMethod.user_id == user_id,
                UserMfaMethod.method_type == MFA_METHOD_TOTP,
                UserMfaMethod.is_enabled.is_(True),
            )
        ).first()
        return row is not None

    def get_totp_status(self, user_id: UUID) -> tuple[bool, bool, UUID | None]:
        """Returns ``(has_enabled, has_pending, pending_method_id)``."""
        rows = self.db.scalars(
            select(UserMfaMethod).where(
                UserMfaMethod.user_id == user_id,
                UserMfaMethod.method_type == MFA_METHOD_TOTP,
            )
        ).all()
        enabled = next((r for r in rows if r.is_enabled), None)
        pending = next((r for r in rows if not r.is_enabled), None)
        if enabled:
            return True, False, None
        if pending:
            return False, True, pending.id
        return False, False, None

    def verify_totp_code(self, user_id: UUID, code: str) -> bool:
        row = self.db.scalars(
            select(UserMfaMethod).where(
                UserMfaMethod.user_id == user_id,
                UserMfaMethod.method_type == MFA_METHOD_TOTP,
                UserMfaMethod.is_enabled.is_(True),
            )
        ).first()
        if not row:
            return False
        secret = get_totp_secret_crypto().decrypt_secret(row.ciphertext)
        return bool(pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1))

    def start_totp_enrollment(self, user: User, *, ip: str | None) -> tuple[UUID, str]:
        if not user.is_platform_admin:
            raise PermissionError("Not a platform administrator")
        existing = self.db.scalars(
            select(UserMfaMethod).where(
                UserMfaMethod.user_id == user.id,
                UserMfaMethod.method_type == MFA_METHOD_TOTP,
            )
        ).all()
        if any(r.is_enabled for r in existing):
            raise ValueError("TOTP is already enabled; disable it before re-enrolling")
        self.db.execute(
            delete(UserMfaMethod).where(
                UserMfaMethod.user_id == user.id,
                UserMfaMethod.method_type == MFA_METHOD_TOTP,
                UserMfaMethod.is_enabled.is_(False),
            )
        )
        secret = pyotp.random_base32()
        enc = get_totp_secret_crypto().encrypt_secret(secret)
        method = UserMfaMethod(
            id=uuid.uuid4(),
            user_id=user.id,
            method_type=MFA_METHOD_TOTP,
            is_enabled=False,
            method_label="Authenticator app",
            ciphertext=enc,
            method_metadata=None,
            verified_at=None,
        )
        self.db.add(method)
        self.db.commit()
        self.db.refresh(method)
        self.audit.log(
            tenant_id=None,
            actor_user_id=user.id,
            event_type="platform.mfa.enrollment_started",
            details={"method_id": str(method.id), "ip": ip},
        )
        self.db.commit()
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="MSPintel Platform")
        return method.id, uri

    def confirm_totp_enrollment(self, user: User, method_id: UUID, code: str, *, ip: str | None) -> None:
        row = self.db.scalars(
            select(UserMfaMethod).where(
                UserMfaMethod.id == method_id,
                UserMfaMethod.user_id == user.id,
                UserMfaMethod.method_type == MFA_METHOD_TOTP,
                UserMfaMethod.is_enabled.is_(False),
            )
        ).first()
        if not row:
            raise ValueError("Enrollment not found")
        secret = get_totp_secret_crypto().decrypt_secret(row.ciphertext)
        if not pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1):
            raise ValueError("Invalid authenticator code")
        # Do not set is_enabled before verification above (row was created with is_enabled=False).
        row.is_enabled = True
        row.verified_at = datetime.now(UTC)
        self.db.commit()
        self.audit.log(
            tenant_id=None,
            actor_user_id=user.id,
            event_type="platform.mfa.enabled",
            details={"method_id": str(method_id), "ip": ip},
        )
        self.db.commit()

    def disable_totp(self, user: User, code: str, *, ip: str | None) -> None:
        row = self.db.scalars(
            select(UserMfaMethod).where(
                UserMfaMethod.user_id == user.id,
                UserMfaMethod.method_type == MFA_METHOD_TOTP,
                UserMfaMethod.is_enabled.is_(True),
            )
        ).first()
        if not row:
            raise ValueError("TOTP is not enabled")
        if not self.verify_totp_code(user.id, code):
            raise ValueError("Invalid authenticator code")
        self.db.delete(row)
        self.db.commit()
        self.audit.log(
            tenant_id=None,
            actor_user_id=user.id,
            event_type="platform.mfa.disabled",
            details={"ip": ip},
        )
        self.db.commit()
