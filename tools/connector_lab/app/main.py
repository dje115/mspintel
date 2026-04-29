from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse

from app.data import CUSTOMER_SCENARIOS, DATASET, SIGNAL_SCENARIOS

app = FastAPI(title="Connector Lab")

API_BEARER_TOKEN = os.getenv("CONNECTOR_LAB_TOKEN", "connector-lab-dev-token")
API_KEY = os.getenv("CONNECTOR_LAB_API_KEY", "connector-lab-api-key")
GLOBAL_MODE = os.getenv("CONNECTOR_LAB_GLOBAL_MODE", "").strip()
SLOW_MS = int(os.getenv("CONNECTOR_LAB_SLOW_MS", "600"))


def _parse_modes(mode: str | None, mode_header: str | None) -> set[str]:
    raw = ",".join(part for part in [GLOBAL_MODE, mode or "", mode_header or ""] if part).strip()
    return {m.strip().lower() for m in raw.split(",") if m.strip()}


def _auth_ok(authorization: str | None, api_key: str | None) -> bool:
    if api_key and api_key == API_KEY:
        return True
    if not authorization:
        return False
    return authorization == f"Bearer {API_BEARER_TOKEN}"


def _enforce_modes(modes: set[str]) -> None:
    if "slow" in modes:
        time.sleep(SLOW_MS / 1000)
    if "auth_failure" in modes:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Connector Lab forced auth failure")
    if "rate_limit" in modes:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Connector Lab forced rate limit")
    if "server_error" in modes:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Connector Lab forced server error")


def _updated_since_filter(rows: list[dict[str, Any]], updated_since: str | None) -> list[dict[str, Any]]:
    if not updated_since:
        return rows
    try:
        threshold = datetime.fromisoformat(updated_since.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid updated_since format") from exc
    out: list[dict[str, Any]] = []
    for row in rows:
        raw = row.get("updated_at")
        if not raw:
            continue
        row_ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if row_ts >= threshold:
            out.append(row)
    return out


def _partial_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    partial: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        copied = dict(row)
        keys = [k for k in copied.keys() if k not in {"id", "updated_at"}]
        if keys:
            drop = keys[idx % len(keys)]
            copied.pop(drop, None)
        partial.append(copied)
    return partial


def _paginate(rows: list[dict[str, Any]], page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    return rows[start:end], total


def _list_resource(
    *,
    vendor: str,
    entity: str,
    page: int,
    page_size: int,
    updated_since: str | None,
    modes: set[str],
) -> dict[str, Any]:
    vendor_data = DATASET.get(vendor, {})
    rows = list(vendor_data.get(entity, []))
    rows = _updated_since_filter(rows, updated_since)
    if "empty" in modes:
        rows = []
    if "partial" in modes:
        rows = _partial_rows(rows)
    page_rows, total = _paginate(rows, page, page_size)
    has_more = page * page_size < total
    return {
        "vendor": vendor,
        "entity": entity,
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": page_rows,
        "has_more": has_more,
        "modes": sorted(modes),
    }


def _list_graph_resource(
    *,
    request: Request,
    entity: str,
    rows: list[dict[str, Any]],
    page: int,
    page_size: int,
) -> dict[str, Any]:
    page_rows, total = _paginate(rows, page, page_size)
    payload: dict[str, Any] = {
        "@odata.context": f"https://graph.microsoft.com/v1.0/$metadata#{entity}",
        "value": page_rows,
    }
    if page * page_size < total:
        q = dict(request.query_params)
        q["page"] = str(page + 1)
        q["page_size"] = str(page_size)
        payload["@odata.nextLink"] = f"{request.url.path}?{urlencode(q)}"
    return payload


async def _api_guard(
    authorization: str | None,
    x_api_key: str | None,
    mode: str | None,
    x_connector_lab_mode: str | None,
) -> set[str]:
    modes = _parse_modes(mode, x_connector_lab_mode)
    _enforce_modes(modes)
    if not _auth_ok(authorization, x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Connector Lab credentials")
    return modes


def _overview_blocks() -> list[dict[str, Any]]:
    endpoints = {
        "autotask": ["/autotask/accounts", "/autotask/contacts", "/autotask/tickets", "/autotask/opportunities", "/autotask/quotes"],
        "itquoter": ["/itquoter/customers", "/itquoter/quotes", "/itquoter/quote-lines", "/itquoter/quote-statuses"],
        "xero": ["/xero/contacts", "/xero/invoices", "/xero/invoice-lines", "/xero/payment-statuses"],
        "m365": [
            "/m365/organization",
            "/m365/users",
            "/m365/subscribedSkus",
            "/m365/users/{id}/licenseDetails",
            "/m365/licence-summary",
            "/m365/mailbox-counts",
            "/m365/hygiene-findings",
        ],
        "veeam": ["/veeam/customers", "/veeam/backup-jobs", "/veeam/workloads", "/veeam/repositories", "/veeam/restore-tests"],
        "3cx": ["/3cx/calls", "/3cx/extensions"],
    }
    blocks: list[dict[str, Any]] = []
    for vendor, paths in endpoints.items():
        data = DATASET.get(vendor, {})
        counts = {k: len(v) for k, v in data.items() if isinstance(v, list)}
        blocks.append(
            {
                "vendor": vendor,
                "base_path": f"/{vendor}",
                "auth": "Authorization: Bearer connector-lab-dev-token or X-API-Key: connector-lab-api-key",
                "paths": paths,
                "counts": counts,
                "behaviors": ["pagination", "updated_since", "auth_failure", "rate_limit", "server_error", "slow", "empty", "partial"],
            }
        )
    return blocks


def _html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 1.5rem; color: #0f172a; background: #f8fafc; }}
    h1, h2 {{ margin-bottom: 0.35rem; }}
    .sub {{ color: #475569; margin-top: 0; }}
    .warn {{ background: #fff7ed; border: 1px solid #fdba74; padding: .7rem; border-radius: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(280px,1fr)); gap: .8rem; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: .85rem; }}
    code {{ background: #eef2ff; padding: .1rem .3rem; border-radius: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e2e8f0; }}
    th, td {{ border-bottom: 1px solid #e2e8f0; text-align: left; padding: .45rem; font-size: 0.92rem; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>{body}</body>
</html>"""


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "connector-lab",
        "status": "ok",
        "dataset_loaded": True,
        "vendors": sorted(DATASET.keys()),
        "global_mode": GLOBAL_MODE or None,
    }


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
def ui_home() -> str:
    cards = []
    for block in _overview_blocks():
        endpoint_links = "".join(f"<li><a href='{p}'>{p}</a></li>" for p in block["paths"])
        behavior = ", ".join(block["behaviors"])
        count_rows = "".join(f"<li>{k}: {v}</li>" for k, v in sorted(block["counts"].items()))
        cards.append(
            f"<section class='card'><h3>{block['vendor'].upper()}</h3>"
            f"<p><strong>Base:</strong> <code>{block['base_path']}</code></p>"
            f"<p><strong>Auth:</strong> {block['auth']}</p>"
            f"<p><strong>Behaviors:</strong> {behavior}</p>"
            f"<p><strong>Entity counts:</strong></p><ul>{count_rows}</ul>"
            f"<p><strong>API explorer:</strong></p><ul>{endpoint_links}</ul>"
            f"<p><a href='/ui/vendor/{block['vendor']}'>Browse {block['vendor']} data</a></p>"
            "</section>"
        )
    body = (
        "<h1>Connector Lab - development mock APIs</h1>"
        "<p class='sub'>Development/testing only. Not a production vendor integration.</p>"
        "<p class='warn'>Use this service to test connector sync, mapping confidence, and product signal behavior without live vendor access.</p>"
        "<p><a href='/ui/scenarios'>Cross-system mapping scenarios</a> | "
        "<a href='/ui/m365-mapping-scenarios'>M365 mapping scenarios</a> | "
        "<a href='/ui/signals'>Product signal scenarios</a> | "
        "<a href='/ui/status'>Status</a></p>"
        f"<div class='grid'>{''.join(cards)}</div>"
    )
    return _html_page("Connector Lab", body)


@app.get("/ui/status", response_class=HTMLResponse)
def ui_status() -> str:
    rows = "".join(
        f"<tr><td>{vendor}</td><td>{', '.join(sorted(data.keys()))}</td></tr>"
        for vendor, data in sorted(DATASET.items())
    )
    body = (
        "<h1>Connector Lab status</h1>"
        "<p class='sub'>Service running and dataset visibility summary.</p>"
        "<table><thead><tr><th>Vendor</th><th>Entities</th></tr></thead><tbody>"
        f"{rows}</tbody></table>"
        f"<p><strong>Global mode:</strong> <code>{GLOBAL_MODE or 'none'}</code></p>"
        "<p><a href='/'>Back to overview</a></p>"
    )
    return _html_page("Connector Lab status", body)


@app.get("/ui/scenarios", response_class=HTMLResponse)
def ui_scenarios() -> str:
    rows = []
    for row in CUSTOMER_SCENARIOS:
        systems = ", ".join(f"{k}: {v or 'missing'}" for k, v in row["systems"].items())
        rows.append(
            f"<tr><td>{row['canonical_name']}</td><td>{row['scenario']}</td><td>{systems}</td></tr>"
        )
    body = (
        "<h1>Cross-system mapping scenarios</h1>"
        "<p class='sub'>Deliberate identity mismatches used to test mapping confidence and review workflows.</p>"
        "<table><thead><tr><th>Canonical customer</th><th>Scenario</th><th>System appearances</th></tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table>"
        "<p><a href='/'>Back to overview</a></p>"
    )
    return _html_page("Connector Lab scenarios", body)


@app.get("/ui/signals", response_class=HTMLResponse)
def ui_signals() -> str:
    items = "".join(f"<li>{item}</li>" for item in SIGNAL_SCENARIOS)
    body = (
        "<h1>Signal scenario view</h1>"
        "<p class='sub'>Product-signal conditions intentionally present in synthetic data.</p>"
        f"<ul>{items}</ul>"
        "<p><a href='/'>Back to overview</a></p>"
    )
    return _html_page("Connector Lab signals", body)


@app.get("/ui/m365-mapping-scenarios", response_class=HTMLResponse)
def ui_m365_mapping_scenarios() -> str:
    rows = DATASET.get("m365", {}).get("lab_scenarios", [])
    table_rows = []
    for row in rows:
        table_rows.append(
            "<tr>"
            f"<td>{row.get('organization_display_name')}</td>"
            f"<td>{row.get('primary_domain')}</td>"
            f"<td>{row.get('canonical_customer_name') or 'none'}</td>"
            f"<td>{row.get('expected_mapping_state')}</td>"
            f"<td>{row.get('scenario')}</td>"
            "</tr>"
        )
    body = (
        "<h1>M365 mapping scenarios (dev-only)</h1>"
        "<p class='sub'>Connector Lab scenario metadata for MSPIntel mapping behavior. This table is not vendor API payload data.</p>"
        "<table><thead><tr><th>Organization</th><th>Primary domain</th><th>Expected canonical customer</th><th>Expected state</th><th>Scenario</th></tr></thead><tbody>"
        f"{''.join(table_rows)}</tbody></table>"
        "<p><a href='/'>Back to overview</a></p>"
    )
    return _html_page("Connector Lab M365 scenarios", body)


@app.get("/ui/vendor/{vendor}", response_class=HTMLResponse)
def ui_vendor(vendor: str) -> str:
    vendor_data = DATASET.get(vendor)
    if not vendor_data:
        return Response(status_code=404)
    sections = []
    for entity, rows in vendor_data.items():
        if not isinstance(rows, list):
            continue
        sample_rows = rows[:6]
        if not sample_rows:
            continue
        cols = sorted({k for r in sample_rows for k in r.keys()})
        head = "".join(f"<th>{c}</th>" for c in cols)
        body_rows = []
        for r in sample_rows:
            tds = "".join(f"<td>{r.get(c, '')}</td>" for c in cols)
            body_rows.append(f"<tr>{tds}</tr>")
        examples = (
            f"<a href='/{vendor}/{entity.replace('_', '-')}'>{vendor}/{entity.replace('_', '-')}</a> | "
            f"<a href='/{vendor}/{entity.replace('_', '-')}?page=1&page_size=2'>pagination</a> | "
            f"<a href='/{vendor}/{entity.replace('_', '-')}?updated_since=2026-01-01T00:00:00Z'>updated_since</a> | "
            f"<a href='/{vendor}/{entity.replace('_', '-')}?mode=empty'>empty</a> | "
            f"<a href='/{vendor}/{entity.replace('_', '-')}?mode=rate_limit'>rate_limit</a> | "
            f"<a href='/{vendor}/{entity.replace('_', '-')}?mode=server_error'>server_error</a> | "
            f"<a href='/{vendor}/{entity.replace('_', '-')}?mode=partial'>partial</a>"
        )
        sections.append(
            f"<section class='card'><h3>{entity}</h3><p>{examples}</p>"
            f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></section>"
        )
    body = (
        f"<h1>{vendor.upper()} data browser</h1>"
        "<p class='sub'>Read-only mock data preview for connector development.</p>"
        f"<div class='grid'>{''.join(sections)}</div>"
        "<p><a href='/'>Back to overview</a></p>"
    )
    return _html_page(f"{vendor} data", body)


@app.get("/autotask/accounts")
async def autotask_accounts(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    x_connector_lab_mode: str | None = Header(default=None),
    mode: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    updated_since: str | None = Query(default=None),
) -> dict[str, Any]:
    modes = await _api_guard(authorization, x_api_key, mode, x_connector_lab_mode)
    return _list_resource(vendor="autotask", entity="accounts", page=page, page_size=page_size, updated_since=updated_since, modes=modes)


@app.get("/autotask/contacts")
async def autotask_contacts(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("autotask", "contacts", request)


@app.get("/autotask/tickets")
async def autotask_tickets(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("autotask", "tickets", request)


@app.get("/autotask/opportunities")
async def autotask_opportunities(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("autotask", "opportunities", request)


@app.get("/autotask/quotes")
async def autotask_quotes(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("autotask", "quotes", request)


@app.get("/itquoter/customers")
async def itquoter_customers(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("itquoter", "customers", request)


@app.get("/itquoter/quotes")
async def itquoter_quotes(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("itquoter", "quotes", request)


@app.get("/itquoter/quote-lines")
async def itquoter_quote_lines(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("itquoter", "quote_lines", request)


@app.get("/itquoter/quote-statuses")
async def itquoter_quote_statuses(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("itquoter", "quote_statuses", request)


@app.get("/xero/contacts")
async def xero_contacts(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("xero", "contacts", request)


@app.get("/xero/invoices")
async def xero_invoices(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("xero", "invoices", request)


@app.get("/xero/invoice-lines")
async def xero_invoice_lines(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("xero", "invoice_lines", request)


@app.get("/xero/payment-statuses")
async def xero_payment_statuses(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("xero", "payment_statuses", request)


@app.get("/m365/organization")
async def m365_organization(request: Request) -> JSONResponse:
    modes = await _api_guard(
        request.headers.get("authorization"),
        request.headers.get("x-api-key"),
        request.query_params.get("mode"),
        request.headers.get("x-connector-lab-mode"),
    )
    rows = list(DATASET.get("m365", {}).get("organization", []))
    rows = _updated_since_filter(rows, request.query_params.get("updated_since"))
    if "empty" in modes:
        rows = []
    if "partial" in modes:
        rows = _partial_rows(rows)
    page = int(request.query_params.get("page", "1"))
    page_size = int(request.query_params.get("page_size", "50"))
    payload = _list_graph_resource(request=request, entity="organization", rows=rows, page=page, page_size=page_size)
    return JSONResponse(payload)


@app.get("/m365/tenants")
async def m365_tenants_legacy_alias(request: Request) -> JSONResponse:
    # Legacy alias for earlier thin-slice tests. Kept vendor-shaped.
    return await m365_organization(request)


@app.get("/m365/users")
async def m365_users(request: Request) -> JSONResponse:
    modes = await _api_guard(
        request.headers.get("authorization"),
        request.headers.get("x-api-key"),
        request.query_params.get("mode"),
        request.headers.get("x-connector-lab-mode"),
    )
    rows = list(DATASET.get("m365", {}).get("users", []))
    rows = _updated_since_filter(rows, request.query_params.get("updated_since"))
    if "empty" in modes:
        rows = []
    if "partial" in modes:
        rows = _partial_rows(rows)
    page = int(request.query_params.get("page", "1"))
    page_size = int(request.query_params.get("page_size", "50"))
    payload = _list_graph_resource(request=request, entity="users", rows=rows, page=page, page_size=page_size)
    return JSONResponse(payload)


@app.get("/m365/subscribedSkus")
async def m365_subscribed_skus(request: Request) -> JSONResponse:
    modes = await _api_guard(
        request.headers.get("authorization"),
        request.headers.get("x-api-key"),
        request.query_params.get("mode"),
        request.headers.get("x-connector-lab-mode"),
    )
    rows = list(DATASET.get("m365", {}).get("subscribed_skus", []))
    rows = _updated_since_filter(rows, request.query_params.get("updated_since"))
    if "empty" in modes:
        rows = []
    if "partial" in modes:
        rows = _partial_rows(rows)
    page = int(request.query_params.get("page", "1"))
    page_size = int(request.query_params.get("page_size", "50"))
    payload = _list_graph_resource(request=request, entity="subscribedSkus", rows=rows, page=page, page_size=page_size)
    return JSONResponse(payload)


@app.get("/m365/users/{user_id}/licenseDetails")
async def m365_user_license_details(user_id: str, request: Request) -> JSONResponse:
    modes = await _api_guard(
        request.headers.get("authorization"),
        request.headers.get("x-api-key"),
        request.query_params.get("mode"),
        request.headers.get("x-connector-lab-mode"),
    )
    rows = list(DATASET.get("m365", {}).get("license_details", []))
    match = next((r for r in rows if str(r.get("user_id")) == user_id), None)
    value = list((match or {}).get("value") or [])
    if "empty" in modes:
        value = []
    payload = {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users('id')/licenseDetails",
        "value": value,
    }
    return JSONResponse(payload)


@app.get("/m365/licence-summary")
async def m365_licence_summary(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("m365", "licence_summary", request)


@app.get("/m365/mailbox-counts")
async def m365_mailbox_counts(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("m365", "mailbox_counts", request)


@app.get("/m365/hygiene-findings")
async def m365_hygiene_findings(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("m365", "hygiene_findings", request)


@app.get("/m365/lab-scenarios")
async def m365_lab_scenarios(request: Request) -> JSONResponse:
    # Development-only metadata endpoint for mapping behavior testing.
    return await _generic_vendor_handler("m365", "lab_scenarios", request)


@app.get("/veeam/customers")
async def veeam_customers(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("veeam", "customers", request)


@app.get("/veeam/backup-jobs")
async def veeam_backup_jobs(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("veeam", "backup_jobs", request)


@app.get("/veeam/workloads")
async def veeam_workloads(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("veeam", "workloads", request)


@app.get("/veeam/repositories")
async def veeam_repositories(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("veeam", "repositories", request)


@app.get("/veeam/restore-tests")
async def veeam_restore_tests(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("veeam", "restore_tests", request)


@app.get("/3cx/calls")
async def c3cx_calls(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("3cx", "calls", request)


@app.get("/3cx/extensions")
async def c3cx_extensions(request: Request) -> JSONResponse:
    return await _generic_vendor_handler("3cx", "extensions", request)


async def _generic_vendor_handler(vendor: str, entity: str, request: Request) -> JSONResponse:
    auth = request.headers.get("authorization")
    key = request.headers.get("x-api-key")
    mode = request.query_params.get("mode")
    mode_header = request.headers.get("x-connector-lab-mode")
    page = int(request.query_params.get("page", "1"))
    page_size = int(request.query_params.get("page_size", "50"))
    updated_since = request.query_params.get("updated_since")
    modes = await _api_guard(auth, key, mode, mode_header)
    # Keep emulator behavior practical: Xero accounting APIs are tenant-header scoped.
    if vendor == "xero" and request.headers.get("xero-tenant-id") is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required Xero-Tenant-Id header")
    payload = _list_resource(
        vendor=vendor,
        entity=entity,
        page=page,
        page_size=page_size,
        updated_since=updated_since,
        modes=modes,
    )
    return JSONResponse(payload)

