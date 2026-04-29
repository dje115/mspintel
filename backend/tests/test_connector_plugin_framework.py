from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.services.connectors.registry import ConnectorRegistry


def test_registry_exposes_manifest_capabilities_and_maturity() -> None:
    reg = ConnectorRegistry()
    manifests = reg.list_manifests()
    assert any(m.key == "autotask" for m in manifests)
    xero = reg.get_manifest("xero")
    assert xero.system_family == "accounting"
    assert xero.maturity in ("experimental", "beta", "stable")
    itq = reg.get_manifest("itquoter")
    assert itq.maturity in ("stub", "planned")
    assert itq.implemented is False


def test_manifest_required_fields_validation() -> None:
    reg = ConnectorRegistry()
    adapter = reg.get("autotask")
    missing = adapter.validate_config("api_key", {"username": "u"})
    assert "base_url" in missing
    missing2 = adapter.validate_config(
        "api_key",
        {"base_url": "https://webservices.autotask.net/atservicesrest/", "username": "u"},
    )
    assert "integration_code" in missing2
    assert "secret" in missing2


def test_connector_scaffold_script_creates_files_and_template() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    providers = backend_root / "app" / "services" / "connectors" / "providers"
    tests_dir = backend_root / "tests"
    key = "scaffold_sample"
    provider_file = providers / f"{key}.py"
    test_file = tests_dir / f"test_connector_{key}_scaffold.py"
    for p in (provider_file, test_file):
        if p.exists():
            p.unlink()
    try:
        cmd = [
            sys.executable,
            str(backend_root / "scripts" / "scaffold_connector.py"),
            "--key",
            key,
            "--display-name",
            "Scaffold Sample",
            "--family",
            "generic",
            "--maturity",
            "planned",
            "--capabilities",
            "customers,contacts",
            "--auth-modes",
            "api_key",
        ]
        run = subprocess.run(cmd, cwd=str(backend_root), check=False, capture_output=True, text=True)
        assert run.returncode == 0, run.stderr or run.stdout
        assert provider_file.exists()
        assert test_file.exists()
        text = provider_file.read_text(encoding="utf-8")
        assert "class ScaffoldSampleConnectorAdapter" in text
        assert 'key="scaffold_sample"' in text
    finally:
        for p in (provider_file, test_file):
            if p.exists():
                p.unlink()

