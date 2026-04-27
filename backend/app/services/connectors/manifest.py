from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ConnectorMaturity = Literal["planned", "stub", "experimental", "beta", "stable"]
AuthMode = Literal["api_key", "oauth2", "oauth", "username_password", "token_endpoint", "sandbox", "none"]
SyncMode = Literal["manual", "delta", "full", "webhook"]
ImportScopeMode = Literal["all", "selected_external_ids", "selected_names", "name_prefix", "sample_limit", "recent_active"]


@dataclass(frozen=True)
class ConnectorConfigField:
    key: str
    label: str
    required: bool = False
    secret: bool = False
    editable_after_create: bool = True
    help_text: str | None = None


@dataclass(frozen=True)
class ConnectorManifest:
    key: str
    display_name: str
    description: str
    system_family: str
    maturity: ConnectorMaturity
    auth_modes: tuple[AuthMode, ...]
    capabilities: tuple[str, ...]
    sync_modes: tuple[SyncMode, ...] = ("manual",)
    connector_version: str = "v1"
    default_cadence_minutes: int = 60
    implemented: bool = False
    config_fields: tuple[ConnectorConfigField, ...] = field(default_factory=tuple)
    import_scope_modes: tuple[ImportScopeMode, ...] = ("all",)
    import_scope_filter_keys: tuple[str, ...] = ()
    ui_help_text: str | None = None

    def required_fields_for_auth(self, auth_mode: str) -> tuple[str, ...]:
        # For now we use a single config field list; future extension can map by auth_mode.
        if auth_mode not in self.auth_modes:
            return ()
        return tuple(f.key for f in self.config_fields if f.required)

    def secret_fields(self) -> tuple[str, ...]:
        return tuple(f.key for f in self.config_fields if f.secret)

