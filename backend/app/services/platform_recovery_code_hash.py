"""Normalize and HMAC-hash platform MFA recovery codes (never store plaintext)."""

from __future__ import annotations

import hashlib
import hmac
from uuid import UUID


def normalize_recovery_code(raw: str) -> str:
    s = raw.strip().upper().replace(" ", "").replace("-", "")
    if len(s) < 8 or len(s) > 64:
        raise ValueError("Invalid recovery code format")
    for ch in s:
        if ch not in "0123456789ABCDEF":
            raise ValueError("Invalid recovery code format")
    return s


def hash_platform_recovery_code(pepper: str, user_id: UUID, normalized: str) -> str:
    key = pepper.encode("utf-8")
    msg = f"{user_id}:{normalized}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def format_recovery_code_for_display(token_hex: str) -> str:
    x = token_hex.upper()
    if len(x) != 10:
        return x
    return f"{x[:5]}-{x[5:]}"
