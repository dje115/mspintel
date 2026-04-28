from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


BASE_TS = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)


CUSTOMER_MASTER = [
    {
        "key": "acme_dental",
        "canonical_name": "Acme Dental Ltd",
        "scenario": "Exact cross-system match with healthy baseline.",
        "hints": {
            "autotask": "Acme Dental Ltd",
            "itquoter": "Acme Dental",
            "xero": "Acme Dental Ltd",
            "m365": "Acme Dental Ltd",
            "veeam": "Acme Dental Ltd",
        },
        "signals": ["exact_match"],
    },
    {
        "key": "bright_legal",
        "canonical_name": "Bright Legal Services",
        "scenario": "Trading vs legal suffix mismatch.",
        "hints": {
            "autotask": "Bright Legal Services",
            "itquoter": "Bright Legal",
            "xero": "Bright Legal Services LLP",
            "m365": "Bright Legal Services",
            "veeam": "Bright Legal Services",
        },
        "signals": ["trading_vs_legal_name", "stalled_quote"],
    },
    {
        "key": "greenfield_school",
        "canonical_name": "Greenfield Primary School",
        "scenario": "Missing suffix and duplicate candidate pressure.",
        "hints": {
            "autotask": "Greenfield Primary School",
            "itquoter": "Greenfield School",
            "xero": "Greenfield Primary",
            "m365": "Greenfield Primary School",
            "veeam": "Greenfield Primary School",
        },
        "signals": ["missing_suffix", "duplicate_candidate"],
    },
    {
        "key": "northview_logistics",
        "canonical_name": "Northview Logistics",
        "scenario": "Missing from backup system to test gap handling.",
        "hints": {
            "autotask": "Northview Logistics",
            "itquoter": "Northview Logistics",
            "xero": "Northview Logistics",
            "m365": "Northview Logistics",
            "veeam": None,
        },
        "signals": ["system_gap"],
    },
    {
        "key": "riverside_care",
        "canonical_name": "Riverside Care Group",
        "scenario": "Legacy naming in backup and high ticket pressure.",
        "hints": {
            "autotask": "Riverside Care Group",
            "itquoter": "Riverside Care",
            "xero": "Riverside Care Group",
            "m365": "Riverside Care Group",
            "veeam": "Riverside Care Group Legacy",
        },
        "signals": ["high_ticket_pressure", "failed_backup_jobs"],
    },
    {
        "key": "old_mill",
        "canonical_name": "Old Mill Engineering",
        "scenario": "Low-confidence sparse profile.",
        "hints": {
            "autotask": "Old Mill Engineering",
            "itquoter": "Old Mill Eng",
            "xero": "Old Mill Engineering",
            "m365": "Old Mill Engineering",
            "veeam": "Old Mill Engineering",
        },
        "signals": ["low_confidence_mapping", "no_recent_contact"],
    },
]


def _add_generated_customers() -> None:
    realistic_names = [
        "Foxglove Accountants Ltd",
        "Harborough Veterinary Clinic",
        "Midland Fabrication Ltd",
        "Ashfield Architects",
        "Brookside Pharmacy",
        "Castle View Estate Agents",
        "Silverline Manufacturing Ltd",
        "Meadowgate Care Home",
        "Oakridge Construction Ltd",
        "Willowbrook Finance",
        "Fosse Retail Group",
        "Welland Dental Care",
        "Stoughton Logistics Ltd",
        "Kingfisher Education Trust",
        "Bruntingthorpe Engineering Ltd",
        "Market Harborough Dental",
        "Leicester Property Services",
        "Rutland Legal LLP",
        "Welford Road Hospitality",
        "Soar Valley Training",
        "Hinckley Components Ltd",
    ]
    for i, name in enumerate(realistic_names, start=1):
        signals = []
        if i % 3 == 0:
            signals.append("stalled_quote")
        if i % 4 == 0:
            signals.append("unpaid_aged_invoice")
        if i % 5 == 0:
            signals.append("m365_licence_mismatch")
        if i % 6 == 0:
            signals.append("inactive_licensed_users")
        if i % 7 == 0:
            signals.append("failed_backup_jobs")
        if i % 8 == 0:
            signals.append("stale_restore_test")
        if i % 9 == 0:
            signals.append("shared_mailboxes_not_billed")
        if not signals:
            signals = ["exact_match"]
        # Keep realistic but intentionally messy cross-system identity variants.
        if i % 6 == 0:
            xero_name = name.replace("Ltd", "Limited").replace("  ", " ").strip()
        elif i % 5 == 0:
            xero_name = name.upper().replace(" LLP", " L.L.P.")
        else:
            xero_name = name
        itq_name = name.replace(" Ltd", "").replace(" LLP", "")
        m365_hint = itq_name if i % 4 else xero_name
        veeam_name = None if i % 5 == 0 else name
        CUSTOMER_MASTER.append(
            {
                "key": f"scenario_{i:02d}",
                "canonical_name": name,
                "scenario": "Realistic UK MSP demo account with deliberate identity variance.",
                "hints": {
                    "autotask": name,
                    "itquoter": itq_name,
                    "xero": xero_name,
                    "m365": m365_hint,
                    "veeam": veeam_name,
                },
                "signals": signals,
            }
        )


_add_generated_customers()


CUSTOMER_SCENARIOS = [
    {
        "customer_key": row["key"],
        "canonical_name": row["canonical_name"],
        "scenario": row["scenario"],
        "systems": {
            "autotask": row["hints"]["autotask"],
            "itquoter": row["hints"]["itquoter"],
            "xero": row["hints"]["xero"],
            "m365": row["hints"]["m365"],
            "veeam": row["hints"]["veeam"],
        },
    }
    for row in CUSTOMER_MASTER
]

SIGNAL_SCENARIOS = [
    "exact customer match",
    "trading name vs legal name",
    "missing Ltd/Limited suffix",
    "duplicate candidate-style naming",
    "unmatched source records",
    "stale/deleted source hints",
    "low-confidence mapping",
    "high ticket pressure",
    "no recent contact",
    "stalled quote",
    "lost quote",
    "accepted quote not invoiced",
    "unpaid aged invoice",
    "M365 licence mismatch",
    "inactive licensed users",
    "shared mailboxes not billed",
    "weak MFA hygiene",
    "Veeam failed jobs",
    "stale backup jobs",
    "no recent restore test",
    "repository/storage growth",
    "customer present in one system only",
]


def _build_dataset() -> dict:
    autotask_accounts = []
    autotask_contacts = []
    autotask_tickets = []
    autotask_opps = []
    autotask_quotes = []
    itquoter_customers = []
    itquoter_quotes = []
    itquoter_quote_lines = []
    xero_contacts = []
    xero_invoices = []
    xero_invoice_lines = []
    m365_tenants = []
    m365_users = []
    m365_licence = []
    m365_mailboxes = []
    m365_hygiene = []
    veeam_customers = []
    veeam_jobs = []
    veeam_workloads = []
    veeam_repos = []
    veeam_restore_tests = []
    calls = []
    extensions = []
    for idx, row in enumerate(CUSTOMER_MASTER, start=1):
        ts = BASE_TS - timedelta(minutes=idx * 6)
        at_id = f"AT-{1000 + idx}"
        itq_id = f"ITQ-C{idx:03d}"
        x_contact = f"{idx:08d}-{idx:04d}-{idx:04d}-{idx:04d}-{idx:012d}"[:36]
        x_inv = f"{idx+100:08d}-{idx+100:04d}-{idx+100:04d}-{idx+100:04d}-{idx+100:012d}"[:36]
        tenant_id = f"M-T{idx:03d}"
        veeam_id = f"V-C{idx:03d}"
        hint = row["hints"]
        signals = set(row["signals"])
        autotask_accounts.append(
            {
                "id": at_id,
                "companyName": hint["autotask"] or row["canonical_name"],
                "name": hint["autotask"] or row["canonical_name"],
                "isActive": "stale_deleted_source" not in signals,
                "ownerResourceName": f"Owner {idx%5+1}",
                "lastActivityDate": _iso(ts),
                "updated_at": _iso(ts),
            }
        )
        autotask_contacts.append(
            {
                "id": f"ATC-{idx:03d}",
                "companyID": at_id,
                "account_id": at_id,
                "firstName": f"Contact{idx}",
                "lastName": "Primary",
                "name": f"Contact{idx} Primary",
                "emailAddress": f"contact{idx}@example-mspintel.test",
                "email": f"contact{idx}@example-mspintel.test",
                "updated_at": _iso(ts),
            }
        )
        ticket_count = 4 if "high_ticket_pressure" in signals else 1
        for t in range(ticket_count):
            autotask_tickets.append(
                {
                    "id": f"ATT-{idx:03d}-{t+1}",
                    "companyID": at_id,
                    "account_id": at_id,
                    "status": "New" if t < 2 else "In Progress",
                    "priority": "high" if "high_ticket_pressure" in signals else "medium",
                    "title": f"Ticket {t+1} for {row['canonical_name']}",
                    "subject": f"Ticket {t+1} for {row['canonical_name']}",
                    "updated_at": _iso(ts - timedelta(minutes=t)),
                }
            )
        autotask_opps.append(
            {
                "id": f"ATO-{idx:03d}",
                "companyID": at_id,
                "account_id": at_id,
                "status": "stalled" if "stalled_quote" in signals else "Open",
                "title": f"Opportunity for {row['canonical_name']}",
                "amount": 12000 + idx * 300,
                "updated_at": _iso(ts),
            }
        )
        autotask_quotes.append(
            {
                "id": f"ATQ-{idx:03d}",
                "companyID": at_id,
                "account_id": at_id,
                "status": "lost" if "lost_quote" in signals else ("open" if "stalled_quote" in signals else "won"),
                "name": f"Quote for {row['canonical_name']}",
                "title": f"Quote for {row['canonical_name']}",
                "totalAmount": 9000 + idx * 250,
                "value": 9000 + idx * 250,
                "updated_at": _iso(ts),
            }
        )
        itquoter_customers.append({"id": itq_id, "name": hint["itquoter"] or row["canonical_name"], "updated_at": _iso(ts)})
        quote_status = "stalled" if "stalled_quote" in signals else ("lost" if "lost_quote" in signals else "won")
        itquoter_quotes.append(
            {"id": f"ITQ-Q{idx:03d}", "customer_id": itq_id, "status": quote_status, "title": f"ITQ quote {idx}", "updated_at": _iso(ts)}
        )
        itquoter_quote_lines.append(
            {
                "id": f"ITQL-{idx:03d}",
                "quote_id": f"ITQ-Q{idx:03d}",
                "sku": f"SKU-{idx:04d}",
                "qty": 1 + (idx % 4),
                "price": 100 + idx * 5,
                "updated_at": _iso(ts),
            }
        )
        xero_contacts.append(
            {
                "id": f"X-C{idx:03d}",
                "ContactID": x_contact,
                "Name": hint["xero"] or row["canonical_name"],
                "name": hint["xero"] or row["canonical_name"],
                "ContactStatus": "ACTIVE",
                "updated_at": _iso(ts),
            }
        )
        amount_due = 0
        age = 0
        if "unpaid_aged_invoice" in signals:
            amount_due = 1500 + idx * 40
            age = 45 + (idx % 30)
        xero_invoices.append(
            {
                "id": f"X-I{idx:03d}",
                "InvoiceID": x_inv,
                "Contact": {"ContactID": x_contact},
                "contact_id": f"X-C{idx:03d}",
                "Status": "AUTHORISED",
                "status": "AUTHORISED",
                "Total": 3000 + idx * 70,
                "total": 3000 + idx * 70,
                "AmountDue": amount_due,
                "amount_due": amount_due,
                "age_days": age,
                "updated_at": _iso(ts),
            }
        )
        xero_invoice_lines.append(
            {
                "id": f"X-L{idx:03d}",
                "invoice_id": f"X-I{idx:03d}",
                "description": f"Managed services line {idx}",
                "qty": 1,
                "unit_amount": 3000 + idx * 70,
                "updated_at": _iso(ts),
            }
        )
        tenant_name = f"{row['key']}.onmicrosoft.com"
        m365_tenants.append(
            {
                "id": tenant_id,
                "tenant_name": tenant_name,
                "customer_hint": hint["m365"] or row["canonical_name"],
                "auto_confirm_customer": bool("exact_match" in signals and idx <= 3),
                "updated_at": _iso(ts),
            }
        )
        licensed = 25 + idx
        active = licensed - (5 if "inactive_licensed_users" in signals else 1)
        m365_licence.append(
            {
                "tenant_id": tenant_id,
                "licensed_users": licensed + (8 if "m365_licence_mismatch" in signals else 0),
                "active_users_30d": active,
                "inactive_users_30d": max(0, licensed - active),
                "updated_at": _iso(ts),
            }
        )
        shared = 12 if "shared_mailboxes_not_billed" in signals else 3
        m365_mailboxes.append(
            {"tenant_id": tenant_id, "mailboxes": active, "shared_mailboxes": shared, "updated_at": _iso(ts)}
        )
        hygiene_code = "weak_mfa_baseline" if "weak_mfa_hygiene" in signals else "inactive_users_still_licensed"
        m365_hygiene.append(
            {"tenant_id": tenant_id, "finding": hygiene_code, "severity": "high" if "weak_mfa_hygiene" in signals else "medium", "updated_at": _iso(ts)}
        )
        m365_users.append(
            {
                "id": f"M-U{idx:04d}",
                "tenant_id": tenant_id,
                "displayName": f"{row['canonical_name']} User",
                "userPrincipalName": f"user{idx}@{tenant_name}",
                "upn": f"user{idx}@{tenant_name}",
                "accountEnabled": True,
                "active_last_30d": "inactive_licensed_users" not in signals,
                "licensed": True,
                "updated_at": _iso(ts),
            }
        )
        if hint["veeam"]:
            veeam_customers.append({"id": veeam_id, "instanceUid": f"{veeam_id}-uid", "name": hint["veeam"], "updated_at": _iso(ts)})
            veeam_jobs.append(
                {
                    "id": f"V-J{idx:03d}",
                    "customer_id": veeam_id,
                    "status": "failed" if "failed_backup_jobs" in signals else ("warning" if "stale_backup_jobs" in signals else "success"),
                    "last_run_at": _iso(ts - timedelta(hours=60 if "stale_backup_jobs" in signals else 3)),
                    "updated_at": _iso(ts),
                }
            )
            veeam_workloads.append(
                {
                    "id": f"V-W{idx:03d}",
                    "customer_id": veeam_id,
                    "workload": "M365 mailbox",
                    "protected": "failed_backup_jobs" not in signals,
                    "updated_at": _iso(ts),
                }
            )
            veeam_repos.append(
                {
                    "id": f"V-R{idx:03d}",
                    "name": f"Repo-{idx:03d}",
                    "health": "degraded" if "repository_growth" in signals else "healthy",
                    "updated_at": _iso(ts),
                }
            )
            veeam_restore_tests.append(
                {
                    "id": f"V-T{idx:03d}",
                    "customer_id": veeam_id,
                    "last_tested_at": _iso(ts - timedelta(days=400 if "stale_restore_test" in signals else 40)),
                    "status": "overdue" if "stale_restore_test" in signals else "ok",
                    "updated_at": _iso(ts),
                }
            )
        calls.append(
            {
                "id": f"C3-{idx:03d}",
                "customer_hint": row["canonical_name"],
                "direction": "outbound",
                "duration_seconds": 0 if "no_recent_contact" in signals else 320,
                "agent": f"Agent {idx%6+1}",
                "started_at": _iso(ts),
                "updated_at": _iso(ts),
            }
        )
        extensions.append({"id": f"EXT-{2000+idx}", "owner": f"Agent {idx%6+1}", "status": "online", "updated_at": _iso(ts)})
    itquoter_statuses = [
        {"code": "draft", "label": "Draft"},
        {"code": "open", "label": "Open"},
        {"code": "stalled", "label": "Stalled"},
        {"code": "lost", "label": "Lost"},
        {"code": "won", "label": "Won"},
        {"code": "accepted_not_invoiced", "label": "Accepted (Not Invoiced)"},
    ]
    payment_statuses = [
        {"code": "PAID", "label": "Paid"},
        {"code": "PARTIAL", "label": "Partially paid"},
        {"code": "UNPAID", "label": "Unpaid"},
    ]
    return {
        "autotask": {
            "accounts": autotask_accounts,
            "contacts": autotask_contacts,
            "tickets": autotask_tickets,
            "opportunities": autotask_opps,
            "quotes": autotask_quotes,
        },
        "itquoter": {
            "customers": itquoter_customers,
            "quotes": itquoter_quotes,
            "quote_lines": itquoter_quote_lines,
            "quote_statuses": itquoter_statuses,
        },
        "xero": {
            "contacts": xero_contacts,
            "invoices": xero_invoices,
            "invoice_lines": xero_invoice_lines,
            "payment_statuses": payment_statuses,
        },
        "m365": {
            "tenants": m365_tenants,
            "users": m365_users,
            "licence_summary": m365_licence,
            "mailbox_counts": m365_mailboxes,
            "hygiene_findings": m365_hygiene,
        },
        "veeam": {
            "customers": veeam_customers,
            "backup_jobs": veeam_jobs,
            "workloads": veeam_workloads,
            "repositories": veeam_repos,
            "restore_tests": veeam_restore_tests,
        },
        "3cx": {
            "calls": calls,
            "extensions": extensions,
        },
    }


DATASET = _build_dataset()

