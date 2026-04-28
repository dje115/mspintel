from fastapi.testclient import TestClient

from app.main import API_BEARER_TOKEN, app


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_BEARER_TOKEN}"}


def _auth_headers_xero() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_BEARER_TOKEN}", "Xero-Tenant-Id": "demo-tenant-id"}


def test_auth_success_and_failure():
    client = TestClient(app)
    denied = client.get("/autotask/accounts")
    assert denied.status_code == 401
    ok = client.get("/autotask/accounts", headers=_auth_headers())
    assert ok.status_code == 200


def test_vendor_endpoints_present():
    client = TestClient(app)
    assert client.get("/itquoter/customers", headers=_auth_headers()).status_code == 200
    assert client.get("/xero/invoices", headers=_auth_headers_xero()).status_code == 200
    assert client.get("/m365/users", headers=_auth_headers()).status_code == 200
    assert client.get("/veeam/backup-jobs", headers=_auth_headers()).status_code == 200
    assert client.get("/3cx/calls", headers=_auth_headers()).status_code == 200


def test_pagination_and_modes():
    client = TestClient(app)
    page = client.get("/autotask/accounts?page=1&page_size=2", headers=_auth_headers())
    body = page.json()
    assert page.status_code == 200
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    rate = client.get("/autotask/accounts?mode=rate_limit", headers=_auth_headers())
    assert rate.status_code == 429


def test_messy_customer_data_exists():
    client = TestClient(app)
    body = client.get("/itquoter/customers", headers=_auth_headers()).json()
    names = {row["name"] for row in body["items"]}
    assert "Acme Dental" in names
    assert "Old Mill Eng" in names


def test_expanded_dataset_counts_and_pagination():
    client = TestClient(app)
    accounts = client.get("/autotask/accounts?page=1&page_size=10", headers=_auth_headers())
    assert accounts.status_code == 200
    data = accounts.json()
    assert data["total"] >= 20
    assert data["has_more"] is True
    assert len(data["items"]) == 10
    tenants = client.get("/m365/tenants", headers=_auth_headers())
    assert tenants.status_code == 200
    assert tenants.json()["total"] >= 20


def test_no_generic_connectorlab_scenario_names_in_m365_tenants():
    client = TestClient(app)
    body = client.get("/m365/tenants", headers=_auth_headers()).json()
    tenant_hints = [str(row.get("customer_hint") or "") for row in body["items"]]
    assert tenant_hints
    assert not any("ConnectorLab Scenario Customer" in hint for hint in tenant_hints)


def test_ui_pages_render():
    client = TestClient(app)
    root = client.get("/")
    assert root.status_code == 200
    assert "Connector Lab - development mock APIs" in root.text
    status_page = client.get("/ui/status")
    assert status_page.status_code == 200
    assert "m365" in status_page.text.lower()

