"""Encrypt tenant AI provider settings at rest (Fernet key derived from integration secret)."""

from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken

from app.core.settings import get_settings


def _fernet() -> Fernet:
    raw = get_settings().integration_encryption_key.strip().encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_settings_payload(payload: dict) -> str:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(data).decode("utf-8")


def decrypt_settings_payload(ciphertext: str) -> dict:
    try:
        raw = _fernet().decrypt(ciphertext.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError) as exc:
        raise ValueError("Invalid AI provider settings ciphertext") from exc


def redact_settings_for_api(payload: dict | None) -> dict | None:
    """Strip secret-like keys before returning to clients."""
    if not payload:
        return None
    blocked = {
        "api_key",
        "api_secret",
        "client_secret",
        "password",
        "token",
        "secret",
        "anthropic_api_key",
        "openai_api_key",
    }
    out = {}
    for k, v in payload.items():
        lk = str(k).lower()
        if any(b in lk for b in blocked):
            out[k] = "[redacted]" if v else None
        else:
            out[k] = v
    return out
