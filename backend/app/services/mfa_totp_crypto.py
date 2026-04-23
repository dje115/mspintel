"""Encrypt TOTP secrets at rest (Fernet).

``method_metadata`` on :class:`app.models.entities.UserMfaMethod` is reserved for WebAuthn
credential JSON and other non-TOTP fields. TOTP shared secrets live only in ``ciphertext``.
"""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.settings import get_settings


class TotpSecretCrypto:
    def __init__(self) -> None:
        raw = get_settings().mfa_totp_encryption_key.strip().encode("utf-8")
        self._fernet = Fernet(raw)

    def encrypt_secret(self, secret_base32: str) -> str:
        payload = json.dumps({"v": 1, "k": "totp", "s": secret_base32})
        return self._fernet.encrypt(payload.encode("utf-8")).decode("utf-8")

    def decrypt_secret(self, ciphertext: str) -> str:
        try:
            raw = self._fernet.decrypt(ciphertext.encode("utf-8"))
            data: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except (InvalidToken, json.JSONDecodeError, KeyError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid MFA ciphertext") from exc
        if data.get("k") != "totp" or not isinstance(data.get("s"), str):
            raise ValueError("Unsupported MFA payload")
        return str(data["s"])


def get_totp_secret_crypto() -> TotpSecretCrypto:
    """Return a crypto helper bound to the current ``MFA_TOTP_ENCRYPTION_KEY`` settings."""
    return TotpSecretCrypto()
