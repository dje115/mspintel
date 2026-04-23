"""Platform-operator TOTP MFA (enrolment, verification, disable).

WebAuthn: store credential payloads in ``UserMfaMethod.method_metadata`` and use
``method_type == \"webauthn\"`` when implemented; keep ``ciphertext`` for encrypted blobs
or empty where metadata alone suffices (product choice at WebAuthn time).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from uuid import UUID

import pyotp
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models.entities import PlatformMfaRecoveryCode, User, UserMfaMethod
from app.services.audit import AuditService
from app.services.mfa_totp_crypto import get_totp_secret_crypto
from app.services.platform_recovery_code_hash import (
    format_recovery_code_for_display,
    hash_platform_recovery_code,
    normalize_recovery_code,
)

MFA_METHOD_TOTP = "totp"
RECOVERY_CODE_COUNT = 10


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
        self.db.execute(delete(PlatformMfaRecoveryCode).where(PlatformMfaRecoveryCode.user_id == user.id))
        self.db.commit()
        self.audit.log(
            tenant_id=None,
            actor_user_id=user.id,
            event_type="platform.mfa.disabled",
            details={"ip": ip},
        )
        self.db.commit()

    def count_unused_recovery_codes(self, user_id: UUID) -> int:
        n = self.db.scalar(
            select(func.count())
            .select_from(PlatformMfaRecoveryCode)
            .where(
                PlatformMfaRecoveryCode.user_id == user_id,
                PlatformMfaRecoveryCode.is_used.is_(False),
            )
        )
        return int(n or 0)

    def generate_recovery_codes(self, user: User, *, ip: str | None) -> tuple[list[str], UUID]:
        if not user.is_platform_admin:
            raise PermissionError("Not a platform administrator")
        if not self.has_enabled_totp(user.id):
            raise ValueError("Enable TOTP before generating recovery codes")

        # Only unused rows are removed; consumed codes stay for audit / abuse review.
        res = self.db.execute(
            delete(PlatformMfaRecoveryCode).where(
                PlatformMfaRecoveryCode.user_id == user.id,
                PlatformMfaRecoveryCode.is_used.is_(False),
            )
        )
        invalidated = int(res.rowcount or 0)
        pepper = get_settings().mfa_recovery_code_pepper
        batch_id = uuid.uuid4()
        display_codes: list[str] = []
        for _ in range(RECOVERY_CODE_COUNT):
            token = secrets.token_hex(5)
            normalized = token.upper()
            digest = hash_platform_recovery_code(pepper, user.id, normalized)
            self.db.add(
                PlatformMfaRecoveryCode(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    batch_id=batch_id,
                    code_hash=digest,
                    is_used=False,
                    used_at=None,
                )
            )
            display_codes.append(format_recovery_code_for_display(token))
        self.db.commit()

        event = (
            "platform.mfa.recovery_codes.regenerated"
            if invalidated > 0
            else "platform.mfa.recovery_codes.generated"
        )
        self.audit.log(
            tenant_id=None,
            actor_user_id=user.id,
            event_type=event,
            details={
                "batch_id": str(batch_id),
                "count": RECOVERY_CODE_COUNT,
                "invalidated_unused": invalidated,
                "ip": ip,
            },
        )
        self.db.commit()
        return display_codes, batch_id

    def verify_and_consume_recovery_code(self, user_id: UUID, raw_code: str, *, ip: str | None) -> bool:
        try:
            normalized = normalize_recovery_code(raw_code)
        except ValueError:
            return False
        pepper = get_settings().mfa_recovery_code_pepper
        digest = hash_platform_recovery_code(pepper, user_id, normalized)
        row = self.db.scalars(
            select(PlatformMfaRecoveryCode)
            .where(
                PlatformMfaRecoveryCode.user_id == user_id,
                PlatformMfaRecoveryCode.code_hash == digest,
                PlatformMfaRecoveryCode.is_used.is_(False),
            )
            .with_for_update()
        ).first()
        if not row:
            return False
        row.is_used = True
        row.used_at = datetime.now(UTC)
        self.db.commit()
        self.audit.log(
            tenant_id=None,
            actor_user_id=user_id,
            event_type="platform.mfa.recovery_code.used",
            details={"code_id": str(row.id), "batch_id": str(row.batch_id), "ip": ip},
        )
        self.db.commit()
        return True
