from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ChatCompletionResult:
    text: str
    raw: dict[str, Any]


class ProviderNotConfiguredError(Exception):
    """Missing API key, base URL, or model."""


class ProviderTransportError(Exception):
    """HTTP or protocol failure."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ProviderUnsupportedError(Exception):
    """Adapter not implemented for this provider family in this release."""
