from __future__ import annotations

from datetime import UTC, datetime


def _iso(ts: str) -> str:
    return datetime.fromisoformat(ts).replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


CUSTOMER_SCENARIOS = [
    {
        "customer_key": "acme_dental",
        "canonical_name": "Acme Dental Ltd",
        "scenario": "Exact match in some systems, slight legal-name differences in others.",
        "systems": {
            "autotask": "Acme Dental Ltd",
            "itquoter": "Acme Dental",
            "xero": "Acme Dental Limited",
            "m365": "acme-dental.onmicrosoft.com",
            "veeam": "Acme Dental Ltd",
        },
    },
    {
        "customer_key": "bright_legal",
        "canonical_name": "Bright Legal Services",
        "scenario": "Trading name vs legal suffix mismatch.",
        "systems": {
            "autotask": "Bright Legal Services",
            "itquoter": "Bright Legal",
            "xero": "Bright Legal Services LLP",
            "m365": "brightlegal.onmicrosoft.com",
            "veeam": "Bright Legal Services",
        },
    },
    {
        "customer_key": "greenfield_school",
        "canonical_name": "Greenfield Primary School",
        "scenario": "Missing company suffix and duplicate candidate risk.",
        "systems": {
            "autotask": "Greenfield Primary School",
            "itquoter": "Greenfield School",
            "xero": "Greenfield Primary",
            "m365": "greenfieldprimary.onmicrosoft.com",
            "veeam": "Greenfield Primary School",
        },
    },
    {
        "customer_key": "northview_logistics",
        "canonical_name": "Northview Logistics",
        "scenario": "Present in PSA + Xero, absent in Veeam (unmatched source record).",
        "systems": {
            "autotask": "Northview Logistics",
            "itquoter": "Northview Logistics",
            "xero": "Northview Logistics",
            "m365": "northviewlogistics.onmicrosoft.com",
            "veeam": None,
        },
    },
    {
        "customer_key": "riverside_care",
        "canonical_name": "Riverside Care Group",
        "scenario": "Duplicate candidate and stale/deleted source hints.",
        "systems": {
            "autotask": "Riverside Care Group",
            "itquoter": "Riverside Care",
            "xero": "Riverside Care Group",
            "m365": "riversidecare.onmicrosoft.com",
            "veeam": "Riverside Care Group - Legacy",
        },
    },
    {
        "customer_key": "old_mill",
        "canonical_name": "Old Mill Engineering",
        "scenario": "Low-confidence case with sparse data and no recent contacts.",
        "systems": {
            "autotask": "Old Mill Engineering",
            "itquoter": "Old Mill Eng",
            "xero": "Old Mill Engineering",
            "m365": "oldmillengineering.onmicrosoft.com",
            "veeam": "Old Mill Engineering",
        },
    },
]


SIGNAL_SCENARIOS = [
    "M365 licensed users differ from billing counts.",
    "Inactive users remain licensed in M365.",
    "Shared mailboxes not represented on billing snapshots.",
    "Veeam failed backup jobs and stale jobs older than 48h.",
    "Veeam restore-test overdue for high-priority customer.",
    "ITQuoter lost quote and stalled quote examples.",
    "Xero unpaid invoice and aged debt for finance risk.",
    "Autotask high ticket volume and low-contact account.",
    "Customer present in one system but missing in another.",
]


DATASET = {
    "autotask": {
        "accounts": [
            {"id": "AT-1001", "companyName": "Acme Dental Ltd", "name": "Acme Dental Ltd", "isActive": True, "ownerResourceName": "M. Patel", "lastActivityDate": _iso("2026-01-09T12:00:00"), "updated_at": _iso("2026-01-09T12:00:00")},
            {"id": "AT-1002", "companyName": "Bright Legal Services", "name": "Bright Legal Services", "isActive": True, "ownerResourceName": "J. Harper", "lastActivityDate": _iso("2026-01-08T09:30:00"), "updated_at": _iso("2026-01-08T09:30:00")},
            {"id": "AT-1003", "companyName": "Greenfield Primary School", "name": "Greenfield Primary School", "isActive": True, "ownerResourceName": "N. Webb", "lastActivityDate": _iso("2026-01-10T07:45:00"), "updated_at": _iso("2026-01-10T07:45:00")},
            {"id": "AT-1004", "companyName": "Northview Logistics", "name": "Northview Logistics", "isActive": True, "ownerResourceName": "S. Lowe", "lastActivityDate": _iso("2026-01-07T16:10:00"), "updated_at": _iso("2026-01-07T16:10:00")},
            {"id": "AT-1005", "companyName": "Riverside Care Group", "name": "Riverside Care Group", "isActive": False, "ownerResourceName": "J. Harper", "lastActivityDate": _iso("2026-01-05T10:00:00"), "updated_at": _iso("2026-01-05T10:00:00")},
            {"id": "AT-1006", "companyName": "Old Mill Engineering", "name": "Old Mill Engineering", "isActive": True, "ownerResourceName": "M. Patel", "lastActivityDate": _iso("2026-01-03T11:20:00"), "updated_at": _iso("2026-01-03T11:20:00")},
        ],
        "contacts": [
            {"id": "ATC-1", "companyID": "AT-1001", "account_id": "AT-1001", "firstName": "Lara", "lastName": "Wells", "name": "Lara Wells", "emailAddress": "lara@acmedental.co.uk", "email": "lara@acmedental.co.uk", "updated_at": _iso("2026-01-09T12:00:00")},
            {"id": "ATC-2", "companyID": "AT-1002", "account_id": "AT-1002", "firstName": "Jon", "lastName": "Bright", "name": "Jon Bright", "emailAddress": "jon@brightlegal.co.uk", "email": "jon@brightlegal.co.uk", "updated_at": _iso("2026-01-06T12:00:00")},
            {"id": "ATC-3", "companyID": "AT-1006", "account_id": "AT-1006", "firstName": "No", "lastName": "Recent Contact", "name": "No Recent Contact", "emailAddress": None, "email": None, "updated_at": _iso("2025-11-14T12:00:00")},
        ],
        "tickets": [
            {"id": "ATT-1", "companyID": "AT-1001", "account_id": "AT-1001", "status": "New", "priority": "high", "title": "Repeated line-of-business outage", "subject": "Repeated line-of-business outage", "updated_at": _iso("2026-01-10T08:00:00")},
            {"id": "ATT-2", "companyID": "AT-1001", "account_id": "AT-1001", "status": "In Progress", "priority": "medium", "title": "Printer queue failures", "subject": "Printer queue failures", "updated_at": _iso("2026-01-10T08:10:00")},
            {"id": "ATT-3", "companyID": "AT-1006", "account_id": "AT-1006", "status": "New", "priority": "low", "title": "Monthly patching question", "subject": "Monthly patching question", "updated_at": _iso("2026-01-02T07:00:00")},
        ],
        "opportunities": [
            {"id": "ATO-1", "companyID": "AT-1002", "account_id": "AT-1002", "status": "Open", "title": "Security posture uplift", "amount": 24000, "updated_at": _iso("2026-01-07T15:00:00")},
            {"id": "ATO-2", "companyID": "AT-1004", "account_id": "AT-1004", "status": "stalled", "title": "Warehouse Wi-Fi refresh", "amount": 12000, "updated_at": _iso("2025-12-18T09:00:00")},
        ],
        "quotes": [
            {"id": "ATQ-1", "companyID": "AT-1005", "account_id": "AT-1005", "status": "lost", "name": "Endpoint modernization", "title": "Endpoint modernization", "totalAmount": 18000, "value": 18000, "updated_at": _iso("2026-01-04T13:00:00")},
            {"id": "ATQ-2", "companyID": "AT-1004", "account_id": "AT-1004", "status": "open", "name": "Network segmentation phase 2", "title": "Network segmentation phase 2", "totalAmount": 9500, "value": 9500, "updated_at": _iso("2025-12-20T08:00:00")},
        ],
    },
    "itquoter": {
        "customers": [
            {"id": "ITQ-C1", "name": "Acme Dental", "updated_at": _iso("2026-01-09T12:00:00")},
            {"id": "ITQ-C2", "name": "Bright Legal", "updated_at": _iso("2026-01-07T12:00:00")},
            {"id": "ITQ-C3", "name": "Greenfield School", "updated_at": _iso("2026-01-08T12:00:00")},
            {"id": "ITQ-C4", "name": "Riverside Care", "updated_at": _iso("2026-01-02T12:00:00")},
            {"id": "ITQ-C5", "name": "Old Mill Eng", "updated_at": _iso("2026-01-01T12:00:00")},
        ],
        "quotes": [
            {"id": "ITQ-Q1", "customer_id": "ITQ-C4", "status": "lost", "title": "Continuity retainer", "updated_at": _iso("2026-01-03T10:00:00")},
            {"id": "ITQ-Q2", "customer_id": "ITQ-C2", "status": "stalled", "title": "Legal sector endpoint hardening", "updated_at": _iso("2025-12-12T10:00:00")},
        ],
        "quote_lines": [
            {"id": "ITQL-1", "quote_id": "ITQ-Q1", "sku": "SEC-RET-01", "qty": 1, "price": 4200, "updated_at": _iso("2026-01-03T10:00:00")},
            {"id": "ITQL-2", "quote_id": "ITQ-Q2", "sku": "M365-ADV-02", "qty": 120, "price": 18, "updated_at": _iso("2025-12-12T10:00:00")},
        ],
        "quote_statuses": [
            {"code": "draft", "label": "Draft"},
            {"code": "open", "label": "Open"},
            {"code": "stalled", "label": "Stalled"},
            {"code": "lost", "label": "Lost"},
            {"code": "won", "label": "Won"},
        ],
    },
    "xero": {
        "contacts": [
            {"id": "X-C1", "ContactID": "11111111-1111-1111-1111-111111111111", "Name": "Acme Dental Limited", "name": "Acme Dental Limited", "ContactStatus": "ACTIVE", "updated_at": _iso("2026-01-08T14:00:00")},
            {"id": "X-C2", "ContactID": "22222222-2222-2222-2222-222222222222", "Name": "Bright Legal Services LLP", "name": "Bright Legal Services LLP", "ContactStatus": "ACTIVE", "updated_at": _iso("2026-01-07T14:00:00")},
            {"id": "X-C3", "ContactID": "33333333-3333-3333-3333-333333333333", "Name": "Northview Logistics", "name": "Northview Logistics", "ContactStatus": "ACTIVE", "updated_at": _iso("2026-01-06T14:00:00")},
            {"id": "X-C4", "ContactID": "44444444-4444-4444-4444-444444444444", "Name": "Old Mill Engineering", "name": "Old Mill Engineering", "ContactStatus": "ACTIVE", "updated_at": _iso("2026-01-05T14:00:00")},
        ],
        "invoices": [
            {"id": "X-I1", "InvoiceID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "Contact": {"ContactID": "11111111-1111-1111-1111-111111111111"}, "contact_id": "X-C1", "Status": "AUTHORISED", "status": "AUTHORISED", "Total": 7200, "total": 7200, "AmountDue": 0, "amount_due": 0, "updated_at": _iso("2026-01-10T08:00:00")},
            {"id": "X-I2", "InvoiceID": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "Contact": {"ContactID": "22222222-2222-2222-2222-222222222222"}, "contact_id": "X-C2", "Status": "AUTHORISED", "status": "AUTHORISED", "Total": 6400, "total": 6400, "AmountDue": 6400, "amount_due": 6400, "age_days": 47, "updated_at": _iso("2026-01-09T08:00:00")},
            {"id": "X-I3", "InvoiceID": "cccccccc-cccc-cccc-cccc-cccccccccccc", "Contact": {"ContactID": "33333333-3333-3333-3333-333333333333"}, "contact_id": "X-C3", "Status": "AUTHORISED", "status": "AUTHORISED", "Total": 5100, "total": 5100, "AmountDue": 1800, "amount_due": 1800, "age_days": 18, "updated_at": _iso("2026-01-08T08:00:00")},
        ],
        "invoice_lines": [
            {"id": "X-L1", "invoice_id": "X-I2", "description": "M365 managed seats", "qty": 180, "unit_amount": 22, "updated_at": _iso("2026-01-09T08:00:00")},
            {"id": "X-L2", "invoice_id": "X-I2", "description": "Backup retention", "qty": 1, "unit_amount": 2440, "updated_at": _iso("2026-01-09T08:00:00")},
        ],
        "payment_statuses": [
            {"code": "PAID", "label": "Paid"},
            {"code": "PARTIAL", "label": "Partially paid"},
            {"code": "UNPAID", "label": "Unpaid"},
        ],
    },
    "m365": {
        "tenants": [
            {"id": "M-T1", "tenant_name": "acme-dental.onmicrosoft.com", "customer_hint": "Acme Dental Ltd", "updated_at": _iso("2026-01-10T09:00:00")},
            {"id": "M-T2", "tenant_name": "brightlegal.onmicrosoft.com", "customer_hint": "Bright Legal Services", "updated_at": _iso("2026-01-09T09:00:00")},
        ],
        "users": [
            {"id": "M-U1", "tenant_id": "M-T1", "displayName": "Acme User 1", "userPrincipalName": "user1@acme-dental.co.uk", "upn": "user1@acme-dental.co.uk", "accountEnabled": True, "active_last_30d": False, "licensed": True, "updated_at": _iso("2026-01-10T09:00:00")},
            {"id": "M-U2", "tenant_id": "M-T1", "displayName": "Acme User 2", "userPrincipalName": "user2@acme-dental.co.uk", "upn": "user2@acme-dental.co.uk", "accountEnabled": True, "active_last_30d": True, "licensed": True, "updated_at": _iso("2026-01-10T09:00:00")},
            {"id": "M-U3", "tenant_id": "M-T2", "displayName": "Bright Paralegal 1", "userPrincipalName": "paralegal1@brightlegal.co.uk", "upn": "paralegal1@brightlegal.co.uk", "accountEnabled": True, "active_last_30d": False, "licensed": True, "updated_at": _iso("2026-01-09T09:00:00")},
        ],
        "licence_summary": [
            {"tenant_id": "M-T1", "licensed_users": 145, "active_users_30d": 98, "inactive_users_30d": 47, "updated_at": _iso("2026-01-10T09:00:00")},
            {"tenant_id": "M-T2", "licensed_users": 86, "active_users_30d": 50, "inactive_users_30d": 36, "updated_at": _iso("2026-01-09T09:00:00")},
        ],
        "mailbox_counts": [
            {"tenant_id": "M-T1", "mailboxes": 132, "shared_mailboxes": 23, "updated_at": _iso("2026-01-10T09:00:00")},
            {"tenant_id": "M-T2", "mailboxes": 78, "shared_mailboxes": 11, "updated_at": _iso("2026-01-09T09:00:00")},
        ],
        "hygiene_findings": [
            {"tenant_id": "M-T1", "finding": "inactive_users_still_licensed", "severity": "medium", "updated_at": _iso("2026-01-10T09:00:00")},
            {"tenant_id": "M-T1", "finding": "shared_mailboxes_not_billed", "severity": "high", "updated_at": _iso("2026-01-10T09:00:00")},
        ],
    },
    "veeam": {
        "customers": [
            {"id": "V-C1", "instanceUid": "v-c1-uid", "name": "Acme Dental Ltd", "updated_at": _iso("2026-01-10T06:00:00")},
            {"id": "V-C2", "instanceUid": "v-c2-uid", "name": "Bright Legal Services", "updated_at": _iso("2026-01-09T06:00:00")},
            {"id": "V-C3", "instanceUid": "v-c3-uid", "name": "Riverside Care Group - Legacy", "updated_at": _iso("2025-11-30T06:00:00")},
        ],
        "backup_jobs": [
            {"id": "V-J1", "customer_id": "V-C1", "status": "failed", "last_run_at": _iso("2026-01-10T03:00:00"), "updated_at": _iso("2026-01-10T06:00:00")},
            {"id": "V-J2", "customer_id": "V-C2", "status": "warning", "last_run_at": _iso("2026-01-06T03:00:00"), "updated_at": _iso("2026-01-09T06:00:00")},
        ],
        "workloads": [
            {"id": "V-W1", "customer_id": "V-C1", "workload": "M365 mailbox", "protected": True, "updated_at": _iso("2026-01-09T06:00:00")},
            {"id": "V-W2", "customer_id": "V-C1", "workload": "File server", "protected": False, "updated_at": _iso("2026-01-09T06:00:00")},
        ],
        "repositories": [
            {"id": "V-R1", "name": "London-Repo-01", "health": "degraded", "updated_at": _iso("2026-01-09T06:00:00")},
        ],
        "restore_tests": [
            {"id": "V-T1", "customer_id": "V-C1", "last_tested_at": _iso("2025-09-01T06:00:00"), "status": "overdue", "updated_at": _iso("2026-01-09T06:00:00")},
        ],
    },
    "3cx": {
        "calls": [
            {
                "id": "C3-1",
                "customer_hint": "Bright Legal Services",
                "direction": "outbound",
                "duration_seconds": 622,
                "agent": "M. Patel",
                "started_at": _iso("2026-01-10T10:20:00"),
                "updated_at": _iso("2026-01-10T10:20:00"),
            },
            {
                "id": "C3-2",
                "customer_hint": "Old Mill Engineering",
                "direction": "outbound",
                "duration_seconds": 0,
                "agent": "J. Harper",
                "started_at": _iso("2025-12-09T14:40:00"),
                "updated_at": _iso("2025-12-09T14:40:00"),
            },
        ],
        "extensions": [
            {"id": "EXT-2001", "owner": "M. Patel", "status": "online", "updated_at": _iso("2026-01-10T10:21:00")},
            {"id": "EXT-2002", "owner": "J. Harper", "status": "away", "updated_at": _iso("2026-01-10T10:15:00")},
        ],
    },
}

