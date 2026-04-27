"""Scaffold an in-repo connector plugin skeleton.

Usage example:
python scripts/scaffold_connector.py --key sage --display-name "Sage Accounting" --family accounting --maturity planned --capabilities billing_accounts,invoices --auth-modes oauth2,sandbox
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _snake(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--family", default="generic")
    parser.add_argument("--maturity", default="planned")
    parser.add_argument("--capabilities", default="customers")
    parser.add_argument("--auth-modes", default="api_key")
    args = parser.parse_args()

    key = _snake(args.key)
    class_name = "".join(part.capitalize() for part in key.split("_")) + "ConnectorAdapter"
    caps = [c.strip() for c in args.capabilities.split(",") if c.strip()]
    auth_modes = [m.strip() for m in args.auth_modes.split(",") if m.strip()]

    root = Path(__file__).resolve().parents[1]
    providers_dir = root / "app" / "services" / "connectors" / "providers"
    tests_dir = root / "tests"
    providers_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    provider_path = providers_dir / f"{key}.py"
    test_path = tests_dir / f"test_connector_{key}_scaffold.py"

    if provider_path.exists() or test_path.exists():
        raise SystemExit(f"Refusing to overwrite existing files: {provider_path} or {test_path}")

    provider_code = f'''from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import SourceSystemConnection
from app.services.connectors.base import ConnectorAdapter
from app.services.connectors.manifest import ConnectorConfigField, ConnectorManifest
from app.services.connectors.types import ConnectorSyncResult, ConnectorSyncStats, ConnectorTestResult


class {class_name}(ConnectorAdapter):
    manifest = ConnectorManifest(
        key="{key}",
        display_name="{args.display_name}",
        description="{args.display_name} connector scaffold.",
        system_family="{args.family}",
        maturity="{args.maturity}",
        auth_modes=({", ".join(repr(m) for m in auth_modes)},),
        capabilities=({", ".join(repr(c) for c in caps)},),
        sync_modes=("manual",),
        implemented=False,
        connector_version="v1",
        config_fields=(
            ConnectorConfigField(key="api_key", label="API key", required=False, secret=True),
        ),
        ui_help_text="Scaffold only; implement validate/test/sync before production use.",
    )

    def test_connection(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
    ) -> ConnectorTestResult:
        return ConnectorTestResult(
            ok=False,
            message="Scaffold connector: implement test_connection().",
            checked_at=datetime.now(UTC),
        )

    def run_sync(
        self,
        *,
        db: Session,
        tenant_id: UUID,
        connection: SourceSystemConnection,
        config: dict,
        cursor: str | None,
    ) -> ConnectorSyncResult:
        return ConnectorSyncResult(
            ok=False,
            message="Scaffold connector: implement run_sync().",
            completed_at=datetime.now(UTC),
            next_cursor=cursor,
            stats=ConnectorSyncStats(warnings=["scaffold connector"]),
        )
'''

    test_code = f'''from app.services.connectors.providers.{key} import {class_name}


def test_{key}_scaffold_manifest() -> None:
    adapter = {class_name}()
    m = adapter.describe()
    assert m.key == "{key}"
    assert m.display_name == "{args.display_name}"
'''

    provider_path.write_text(provider_code, encoding="utf-8")
    test_path.write_text(test_code, encoding="utf-8")
    print(f"Created: {{provider_path}}")
    print(f"Created: {{test_path}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

