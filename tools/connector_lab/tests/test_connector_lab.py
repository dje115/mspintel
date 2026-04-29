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
    orgs = client.get("/m365/organization?page=1&page_size=10", headers=_auth_headers())
    assert orgs.status_code == 200
    payload = orgs.json()
    assert len(payload["value"]) == 10
    assert "@odata.nextLink" in payload


def test_m365_vendor_payload_excludes_internal_control_fields():
    client = TestClient(app)
    body = client.get("/m365/organization", headers=_auth_headers()).json()
    rows = body["value"]
    assert rows
    serialized = str(rows[0])
    assert "auto_confirm_customer" not in serialized
    assert "customer_hint" not in serialized
    assert "mapping_status" not in serialized


def test_m365_lab_scenarios_separated_from_vendor_payload():
    client = TestClient(app)
    scen = client.get("/m365/lab-scenarios", headers=_auth_headers())
    assert scen.status_code == 200
    items = scen.json()["items"]
    assert items
    assert "expected_mapping_state" in items[0]
    org = client.get("/m365/organization", headers=_auth_headers()).json()["value"][0]
    assert "expected_mapping_state" not in org


def test_ui_pages_render():
    client = TestClient(app)
    root = client.get("/")
    assert root.status_code == 200
    assert "Connector Lab - development mock APIs" in root.text
    status_page = client.get("/ui/status")
    assert status_page.status_code == 200
    assert "m365" in status_page.text.lower()

