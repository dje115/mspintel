"""Replace workspace data for the demo MSP tenant with a rich synthetic UK dataset.

Every `seed_all` run refreshes this tenant's customers, tickets, quotes, etc.
Other tenants are untouched. All names/companies are fictional.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.ai_settings_crypto import encrypt_settings_payload
from app.models.entities import (
    AccountScore,
    Action,
    AITaskRun,
    Contact,
    Customer,
    IntegrationSyncRun,
    Opportunity,
    Quote,
    Recommendation,
    SourceEntityMapping,
    SourceSystemConnection,
    Tenant,
    Ticket,
)
from app.services.finance_canonical import upsert_finance_for_customer

DEMO_TENANT_SLUG = "demo-msp"

OWNERS = ("Tenant Admin", "Sales User", "Service Manager")


def _demo_profile(
    *,
    industry: str,
    city_line: str,
    billing: dict[str, Any],
    microsoft_365: dict[str, Any],
    backup: dict[str, Any],
    relationship: dict[str, Any],
    data_quality: dict[str, Any],
    scenario_note: str,
) -> dict[str, Any]:
    return {
        "synthetic": True,
        "uk_demo": True,
        "industry": industry,
        "city_line": city_line,
        "billing": billing,
        "microsoft_365": microsoft_365,
        "backup": backup,
        "relationship": relationship,
        "data_quality": data_quality,
        "scenario_note": scenario_note,
    }


# Each row: name, status, industry, city_line, scenario_note,
# billing, m365, backup, rel, dq dicts,
# contacts [(name, email)], tickets [(status, subject)], opps [(status, title, cents|None)],
# quotes [(status, title, cents|None)], recs [(scope, summary)], actions [str], scores (r,a,g)
ACCOUNT_SPECS: list[tuple[Any, ...]] = [
    (
        "Aldwych Dental Group LLP",
        "active",
        "Healthcare / dental",
        "London, Greater London",
        "High-value; healthy relationship; QBR current; no billing drift.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 42,
            "active_mailboxes_measured": 41,
            "storage_tb_billed": 6.0,
            "storage_tb_used": 6.1,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 45,
            "active_sign_ins_30d": 43,
            "mfa_coverage_pct": 96,
            "unused_licences": 1,
            "hygiene": "Strong baseline; Conditional Access enforced.",
        },
        {
            "protected_tb": 14.2,
            "billed_tb": 14.0,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 45,
        },
        {
            "days_since_strategic_touch": 21,
            "stakeholder_count": 5,
            "last_qbr_days_ago": 75,
            "notes": "Monthly vCIO cadence; clinical lead engaged.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Dr Priya Shah", "priya.shah@aldwych-dental.example.com"),
            ("James O'Neill", "j.oneill@aldwych-dental.example.com"),
        ],
        [("open", "Printer scan-to-email queue stuck on reception MFP")],
        [("open", "Microsoft 365 E5 uplift — security workshop follow-up", 1850000)],
        [("open", "Backup storage tier review FY26", 420000)],
        [
            ("executive", "Maintain cadence: exec sponsor happy; propose Teams telephony pilot for branches."),
            ("sales", "E5 uplift still open — align to QBR narrative on Defender for Cloud Apps."),
        ],
        ["Log QBR outcome in PSA after next visit."],
        (22, 18, 71),
    ),
    (
        "Beaconridge Housing Association",
        "at_risk",
        "Social housing / property",
        "Leeds, West Yorkshire",
        "Many tickets; no review 14+ months; service noise masking relationship risk.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 220,
            "active_mailboxes_measured": 238,
            "storage_tb_billed": 48,
            "storage_tb_used": 51.2,
            "aged_debt_gbp": 18400,
            "invoice_friction": "overdue_60_plus",
        },
        {
            "licensed_users": 250,
            "active_sign_ins_30d": 198,
            "mfa_coverage_pct": 58,
            "unused_licences": 12,
            "hygiene": "Legacy shared mailboxes; weak MFA on contractors.",
        },
        {
            "protected_tb": 112,
            "billed_tb": 98,
            "failed_jobs_7d": 5,
            "last_restore_test_days_ago": 410,
        },
        {
            "days_since_strategic_touch": 240,
            "stakeholder_count": 2,
            "last_qbr_days_ago": 430,
            "notes": "Only housing officers on tickets; no economic buyer in CRM.",
        },
        {"missing_fields": ["economic_buyer", "signed_MSA_renewal"], "confidence": "medium_low"},
        [
            ("Karen Whitfield", "k.whitfield@beaconridge-ha.example.com"),
        ],
        [
            ("open", "Housing repairs portal SSO error after Entra change"),
            ("open", "Repeated VPN drops for remote repairs coordinators"),
            ("open", "Print server spooler crash — third occurrence"),
            ("open", "Antivirus policy conflict on Windows 11 estate"),
            ("resolved", "Mailbox migration rollback request (resolved pending verification)"),
        ],
        [("open", "Estate CCTV refresh — stalled procurement", 920000)],
        [("lost", "Lost: backup appliance refresh — budget frozen", 2100000)],
        [
            ("executive", "Schedule exec QBR: debt + ticket velocity + MFA gap are combined churn signals."),
            ("service", "Triage top 5 repeat incidents; assign service manager war-room."),
        ],
        ["Book QBR with CEO and finance; attach aged-debt narrative."],
        (88, 82, 28),
    ),
    (
        "Caledonian Freight & Cold Chain Ltd",
        "watch",
        "Logistics / transport",
        "Glasgow, Scotland",
        "Under-billed M365 vs measured usage; commercial upside.",
        {
            "source_sim": "sage",
            "currency": "GBP",
            "billed_m365_seats": 88,
            "active_mailboxes_measured": 104,
            "storage_tb_billed": 9,
            "storage_tb_used": 9.4,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 110,
            "active_sign_ins_30d": 101,
            "mfa_coverage_pct": 81,
            "unused_licences": 0,
            "hygiene": "Good; opportunity is licence reconciliation vs HR roster.",
        },
        {
            "protected_tb": 36,
            "billed_tb": 35,
            "failed_jobs_7d": 1,
            "last_restore_test_days_ago": 95,
        },
        {
            "days_since_strategic_touch": 55,
            "stakeholder_count": 4,
            "last_qbr_days_ago": 120,
            "notes": "Ops director engaged; IT manager stretched.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Moira Campbell", "moira.c@caledonian-cold.example.com"),
            ("Sanjeev Patel", "sanjeev.p@caledonian-cold.example.com"),
        ],
        [("open", "Telematics gateway TLS cert expiring in 18 days")],
        [("open", "M365 seat true-up before renewal window", 340000)],
        [],
        [
            ("sales", "Commercial: seat count drift +365 days — prepare true-up pack for finance."),
            ("executive", "Position Defender for Office 365 alongside telematics security story."),
        ],
        [],
        (38, 52, 74),
    ),
    (
        "Dartmoor Legal Services Ltd",
        "active",
        "Legal",
        "Exeter, Devon",
        "Invoice friction: disputed line on support retainer; otherwise healthy.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 62,
            "active_mailboxes_measured": 61,
            "storage_tb_billed": 11,
            "storage_tb_used": 10.6,
            "aged_debt_gbp": 6200,
            "invoice_friction": "disputed_line_item",
        },
        {
            "licensed_users": 64,
            "active_sign_ins_30d": 60,
            "mfa_coverage_pct": 100,
            "unused_licences": 0,
            "hygiene": "Excellent; Purview labels pilot candidate.",
        },
        {
            "protected_tb": 22,
            "billed_tb": 22,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 30,
        },
        {
            "days_since_strategic_touch": 14,
            "stakeholder_count": 6,
            "last_qbr_days_ago": 90,
            "notes": "Managing partner wants quarterly security attestations.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Helena Vaughan", "h.vaughan@dartmoor-legal.example.com"),
            ("Oliver Trent", "oliver.trent@dartmoor-legal.example.com"),
        ],
        [("open", "Retainer hours query — finance dispute ticket")],
        [],
        [("open", "Purview sensitivity labels rollout", 480000)],
        [
            ("executive", "Resolve billing dispute before renewal; pair with Purview win story."),
        ],
        ["Partner call with finance + managing partner this week."],
        (28, 44, 62),
    ),
    (
        "Elmwood Academy Trust",
        "watch",
        "Education / multi-academy trust",
        "Nottingham, Nottinghamshire",
        "Low contact beyond helpdesk; safeguarding stakeholders thinly mapped.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 540,
            "active_mailboxes_measured": 512,
            "storage_tb_billed": 120,
            "storage_tb_used": 118,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 560,
            "active_sign_ins_30d": 505,
            "mfa_coverage_pct": 88,
            "unused_licences": 40,
            "hygiene": "Student licence mix; some unused A3 for staff who left.",
        },
        {
            "protected_tb": 210,
            "billed_tb": 205,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 200,
        },
        {
            "days_since_strategic_touch": 120,
            "stakeholder_count": 3,
            "last_qbr_days_ago": 300,
            "notes": "Only IT lead on strategic threads; DfE contact not in CRM.",
        },
        {"missing_fields": ["safeguarding_lead_contact", "multi_academy_CEO"], "confidence": "medium"},
        [
            ("Chris Alder", "c.alder@elmwood-trust.example.com"),
        ],
        [("open", "Classroom device Intune sync backlog after half-term")],
        [("stalled", "Trust-wide SIEM-lite monitoring — stalled in governance", 0)],
        [],
        [
            ("executive", "Map safeguarding + CEO stakeholders; propose education-sector QBR template."),
            ("service", "Reduce Intune backlog SLA breaches before term start."),
        ],
        [],
        (46, 58, 48),
    ),
    (
        "Firthside Manufacturing PLC",
        "active",
        "Manufacturing",
        "Sheffield, South Yorkshire",
        "Backup storage growth vs flat billing — margin risk for MSP.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 130,
            "active_mailboxes_measured": 128,
            "storage_tb_billed": 28,
            "storage_tb_used": 36.8,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 135,
            "active_sign_ins_30d": 122,
            "mfa_coverage_pct": 77,
            "unused_licences": 2,
            "hygiene": "Acceptable; OT segmentation project pending.",
        },
        {
            "protected_tb": 88,
            "billed_tb": 70,
            "failed_jobs_7d": 2,
            "last_restore_test_days_ago": 150,
        },
        {
            "days_since_strategic_touch": 35,
            "stakeholder_count": 4,
            "last_qbr_days_ago": 100,
            "notes": "Plant manager sceptical of cloud backup; prefers tape narrative.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Rachel Byrne", "r.byrne@firthside-mfg.example.com"),
            ("Tom Henshaw", "t.henshaw@firthside-mfg.example.com"),
        ],
        [("open", "Hyper-V replica lag on DR site")],
        [("open", "OT segmentation workshop follow-up", 1200000)],
        [],
        [
            ("sales", "Reprice backup storage tier vs measured TB growth; attach restore-test evidence."),
            ("executive", "Tie backup workshop invite to ransomware tabletop story."),
        ],
        ["Draft storage true-up slide for next ops review."],
        (34, 41, 66),
    ),
    (
        "Glenmore Precision Engineering Ltd",
        "watch",
        "Engineering / CNC",
        "Inverness, Scotland",
        "Stalled quote — cybersecurity bundle — no AM follow-up 90 days.",
        {
            "source_sim": "sage",
            "currency": "GBP",
            "billed_m365_seats": 38,
            "active_mailboxes_measured": 37,
            "storage_tb_billed": 7,
            "storage_tb_used": 6.9,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 40,
            "active_sign_ins_30d": 36,
            "mfa_coverage_pct": 69,
            "unused_licences": 0,
            "hygiene": "MFA gaps on shop-floor shared PCs.",
        },
        {
            "protected_tb": 15,
            "billed_tb": 15,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 60,
        },
        {
            "days_since_strategic_touch": 95,
            "stakeholder_count": 2,
            "last_qbr_days_ago": 200,
            "notes": "Owner-driven; weak secondary stakeholder coverage.",
        },
        {"missing_fields": ["secondary_stakeholder"], "confidence": "medium"},
        [
            ("Dougal Fraser", "dougal.f@glenmore-precision.example.com"),
        ],
        [],
        [],
        [
            ("draft", "Cyber bundle: Defender + backup immutable copies — awaiting sign-off", 280000),
        ],
        [
            ("sales", "Stalled quote >90d — re-engage owner with ROI on immutable backups."),
        ],
        ["AM call script: lead with shop-floor MFA + immutable backup pairing."],
        (40, 49, 55),
    ),
    (
        "Harbourlight Retail Group Ltd",
        "active",
        "Retail / multichannel",
        "Brighton, East Sussex",
        "Good service; weak stakeholder map — only IT + finance known.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 95,
            "active_mailboxes_measured": 94,
            "storage_tb_billed": 18,
            "storage_tb_used": 17.2,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 100,
            "active_sign_ins_30d": 92,
            "mfa_coverage_pct": 85,
            "unused_licences": 6,
            "hygiene": "Solid; Teams Phone System opportunity at warehouses.",
        },
        {
            "protected_tb": 40,
            "billed_tb": 39,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 88,
        },
        {
            "days_since_strategic_touch": 40,
            "stakeholder_count": 2,
            "last_qbr_days_ago": 150,
            "notes": "No COO/ops buyer in CRM — risk on renewal politics.",
        },
        {"missing_fields": ["coo_contact", "store_ops_lead"], "confidence": "medium"},
        [
            ("Nina Brooks", "n.brooks@harbourlight-retail.example.com"),
        ],
        [("open", "Wi-Fi guest portal certificate renewal")],
        [("open", "Warehouse handheld scanner Wi-Fi roaming issues", 0)],
        [],
        [
            ("executive", "Stakeholder map gap: add COO + regional ops before renewal."),
        ],
        ["Research LinkedIn for COO; warm intro via finance sponsor."],
        (30, 36, 68),
    ),
    (
        "Iverson Care at Home CIC",
        "at_risk",
        "Healthcare / domiciliary care",
        "Cardiff, Wales",
        "Data-poor: missing primary mobile for on-call; CIW audit season pressure.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 55,
            "active_mailboxes_measured": 50,
            "storage_tb_billed": 4,
            "storage_tb_used": 4.1,
            "aged_debt_gbp": 900,
            "invoice_friction": "minor_queries",
        },
        {
            "licensed_users": 58,
            "active_sign_ins_30d": 44,
            "mfa_coverage_pct": 52,
            "unused_licences": 0,
            "hygiene": "Shared device MFA weak; carers use personal mobiles for Teams.",
        },
        {
            "protected_tb": 9,
            "billed_tb": 9,
            "failed_jobs_7d": 3,
            "last_restore_test_days_ago": 500,
        },
        {
            "days_since_strategic_touch": 10,
            "stakeholder_count": 2,
            "last_qbr_days_ago": 60,
            "notes": "High staff turnover; roster data stale in PSA.",
        },
        {"missing_fields": ["primary_on_call_mobile", "registered_manager_direct_line"], "confidence": "low"},
        [],
        [("open", "Carer tablet offline sync failures — urgent roster impact")],
        [],
        [],
        [
            ("service", "Data quality: capture on-call mobile + CIW registered manager contacts."),
            ("executive", "Backup failures + weak MFA = regulatory story for QBR."),
        ],
        ["Field visit: validate carer device baseline and MFA options."],
        (79, 74, 22),
    ),
    (
        "Jubilee Property Management Ltd",
        "active",
        "Property management",
        "Birmingham, West Midlands",
        "Strong upsell: Teams Phone + Power Platform for arrears workflow.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 70,
            "active_mailboxes_measured": 69,
            "storage_tb_billed": 14,
            "storage_tb_used": 13.1,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 72,
            "active_sign_ins_30d": 68,
            "mfa_coverage_pct": 90,
            "unused_licences": 0,
            "hygiene": "Clean; ripe for Teams Phone + Power Automate.",
        },
        {
            "protected_tb": 26,
            "billed_tb": 26,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 40,
        },
        {
            "days_since_strategic_touch": 18,
            "stakeholder_count": 5,
            "last_qbr_days_ago": 70,
            "notes": "Finance lead wants automation on arrears letters.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Amelia Grant", "a.grant@jubilee-pm.example.com"),
            ("Leo Martin", "leo.martin@jubilee-pm.example.com"),
        ],
        [("open", "Power Automate flow failing on SharePoint permissions change")],
        [("open", "Teams Phone System pilot — estate agent hunt group", 650000)],
        [],
        [
            ("sales", "Upsell: package Teams Phone + arrears automation with measurable ROI."),
        ],
        [],
        (24, 30, 81),
    ),
    (
        "Kingsford Architects LLP",
        "active",
        "Architecture",
        "Edinburgh, Scotland",
        "No M365 hygiene issues; steady consumption — reference-style account.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 34,
            "active_mailboxes_measured": 34,
            "storage_tb_billed": 8,
            "storage_tb_used": 7.8,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 36,
            "active_sign_ins_30d": 34,
            "mfa_coverage_pct": 100,
            "unused_licences": 0,
            "hygiene": "No material issues; optional Copilot trial for partners.",
        },
        {
            "protected_tb": 19,
            "billed_tb": 19,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 25,
        },
        {
            "days_since_strategic_touch": 30,
            "stakeholder_count": 4,
            "last_qbr_days_ago": 110,
            "notes": "Partners cautious on AI; prefer reference customers for Copilot.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Freya MacLeod", "f.macleod@kingsford-arch.example.com"),
        ],
        [],
        [],
        [],
        [
            ("executive", "Reference account: use for Copilot governance case study if they opt in."),
        ],
        [],
        (18, 22, 58),
    ),
    (
        "Lynmouth Marine Insurance Brokers Ltd",
        "watch",
        "Insurance broking",
        "Plymouth, Devon",
        "Payment friction: cash collection stretched; compliance workload rising.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 48,
            "active_mailboxes_measured": 47,
            "storage_tb_billed": 10,
            "storage_tb_used": 10.5,
            "aged_debt_gbp": 11200,
            "invoice_friction": "cash_collection_stretched",
        },
        {
            "licensed_users": 50,
            "active_sign_ins_30d": 46,
            "mfa_coverage_pct": 92,
            "unused_licences": 0,
            "hygiene": "Good; DLP policies need refresh for FCA data classes.",
        },
        {
            "protected_tb": 21,
            "billed_tb": 21,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 70,
        },
        {
            "days_since_strategic_touch": 22,
            "stakeholder_count": 3,
            "last_qbr_days_ago": 95,
            "notes": "CFO sensitive to cash; wants predictable monthly billing.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Harriet Cole", "h.cole@lynmouth-marine.example.com"),
        ],
        [("open", "DLP alert tuning for client policy packs")],
        [],
        [],
        [
            ("executive", "Align payment plan conversation with DLP/compliance roadmap."),
        ],
        ["Prepare aged-debt timeline export for CFO meeting."],
        (36, 48, 52),
    ),
    (
        "Merseyline Construction Group Ltd",
        "active",
        "Construction",
        "Liverpool, Merseyside",
        "Weak backup posture: long restore-test gap; site offices fragile.",
        {
            "source_sim": "sage",
            "currency": "GBP",
            "billed_m365_seats": 112,
            "active_mailboxes_measured": 108,
            "storage_tb_billed": 22,
            "storage_tb_used": 23.4,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 118,
            "active_sign_ins_30d": 99,
            "mfa_coverage_pct": 63,
            "unused_licences": 4,
            "hygiene": "Site trailers on basic Business Premium; MFA inconsistent.",
        },
        {
            "protected_tb": 54,
            "billed_tb": 52,
            "failed_jobs_7d": 4,
            "last_restore_test_days_ago": 600,
        },
        {
            "days_since_strategic_touch": 45,
            "stakeholder_count": 4,
            "last_qbr_days_ago": 130,
            "notes": "HSE documentation stored on local NAS at sites — shadow IT risk.",
        },
        {"missing_fields": ["site_nas_inventory"], "confidence": "medium"},
        [
            ("Sean Doyle", "s.doyle@merseyline-construct.example.com"),
            ("Aisha Khan", "a.khan@merseyline-construct.example.com"),
        ],
        [
            ("open", "Site trailer backup job failures after power brownout"),
            ("open", "Project file sync conflict between SharePoint and NAS"),
        ],
        [("open", "Immutable backup + NAS retirement project", 2400000)],
        [],
        [
            ("service", "Restore-test overdue + job failures: propose remediation sprint."),
            ("sales", "Workshop: backup + ransomware tabletop for site managers."),
        ],
        [],
        (52, 55, 44),
    ),
    (
        "Northbridge Academy",
        "watch",
        "Education / single school",
        "York, North Yorkshire",
        "Obvious M365 optimisation: unused A1 seats after leavers not reclaimed.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 120,
            "active_mailboxes_measured": 102,
            "storage_tb_billed": 25,
            "storage_tb_used": 24.0,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 130,
            "active_sign_ins_30d": 101,
            "mfa_coverage_pct": 91,
            "unused_licences": 22,
            "hygiene": "Leaver reclaim backlog; Student Use Benefit not tracked.",
        },
        {
            "protected_tb": 48,
            "billed_tb": 47,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 110,
        },
        {
            "days_since_strategic_touch": 50,
            "stakeholder_count": 3,
            "last_qbr_days_ago": 160,
            "notes": "Bursar cost-focused; head less technical.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Peter Hargreaves", "p.hargreaves@northbridge-academy.example.com"),
        ],
        [("open", "Chromebook enrolment errors after OU move")],
        [],
        [],
        [
            ("sales", "M365 optimisation: reclaim unused A1; propose lifecycle automation."),
        ],
        [],
        (32, 40, 63),
    ),
    (
        "Orwell Digital Media Ltd",
        "active",
        "Media / creative",
        "Manchester, Greater Manchester",
        "Ideal for backup + Microsoft + AI governance event invite narrative.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 28,
            "active_mailboxes_measured": 28,
            "storage_tb_billed": 42,
            "storage_tb_used": 61.0,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 30,
            "active_sign_ins_30d": 29,
            "mfa_coverage_pct": 87,
            "unused_licences": 0,
            "hygiene": "Large video assets in SharePoint; sensitivity labels partial.",
        },
        {
            "protected_tb": 95,
            "billed_tb": 70,
            "failed_jobs_7d": 1,
            "last_restore_test_days_ago": 55,
        },
        {
            "days_since_strategic_touch": 12,
            "stakeholder_count": 3,
            "last_qbr_days_ago": 45,
            "notes": "Creative director interested in generative AI governance session.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Zoe Ashford", "z.ashford@orwell-digital.example.com"),
        ],
        [("open", "Render farm VPN throughput complaints")],
        [("open", "Copilot governance workshop — sponsor identified", 0)],
        [],
        [
            ("sales", "Event fit: invite to AI governance + immutable storage workshop (post-production angle)."),
        ],
        [],
        (26, 34, 77),
    ),
    (
        "Penrith Outdoor Equipment Co Ltd",
        "watch",
        "Retail / outdoor",
        "Penrith, Cumbria",
        "No recent commercial activity beyond renewals — dormancy risk.",
        {
            "source_sim": "sage",
            "currency": "GBP",
            "billed_m365_seats": 18,
            "active_mailboxes_measured": 18,
            "storage_tb_billed": 3,
            "storage_tb_used": 2.9,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 20,
            "active_sign_ins_30d": 17,
            "mfa_coverage_pct": 80,
            "unused_licences": 0,
            "hygiene": "Unremarkable.",
        },
        {
            "protected_tb": 6,
            "billed_tb": 6,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 130,
        },
        {
            "days_since_strategic_touch": 200,
            "stakeholder_count": 2,
            "last_qbr_days_ago": 400,
            "notes": "No new opps logged in 18 months.",
        },
        {"missing_fields": ["growth_sponsor"], "confidence": "medium_low"},
        [
            ("Mark Ellison", "m.ellison@penrith-outdoor.example.com"),
        ],
        [],
        [],
        [("lost", "Lost: SD-WAN refresh — chose carrier-direct", 890000)],
        [
            ("sales", "Commercial dormancy: run win-back campaign on e-commerce peak season."),
        ],
        [],
        (44, 51, 33),
    ),
    (
        "Quayside Hospitality Group Ltd",
        "active",
        "Hospitality",
        "Newcastle upon Tyne, Tyne and Wear",
        "Over-served on support tickets relative to contract — margin erosion.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 65,
            "active_mailboxes_measured": 64,
            "storage_tb_billed": 9,
            "storage_tb_used": 8.7,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 68,
            "active_sign_ins_30d": 62,
            "mfa_coverage_pct": 84,
            "unused_licences": 0,
            "hygiene": "OK; guest Wi-Fi integrations noisy.",
        },
        {
            "protected_tb": 17,
            "billed_tb": 17,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 40,
        },
        {
            "days_since_strategic_touch": 8,
            "stakeholder_count": 4,
            "last_qbr_days_ago": 60,
            "notes": "High ticket volume vs contracted hours — tension with ops director.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Imogen Clarke", "i.clarke@quayside-hosp.example.com"),
        ],
        [
            ("open", "POS integration timeout during dinner service"),
            ("open", "Guest Wi-Fi captive portal branding broken after cert update"),
            ("open", "Kitchen printer random offline"),
        ],
        [],
        [],
        [
            ("service", "Ticket load vs contract: propose paid optimisation block or scope reset."),
        ],
        [],
        (41, 63, 40),
    ),
    (
        "Redcliffe Biotech Startup Ltd",
        "watch",
        "Life sciences / startup",
        "Cambridge, Cambridgeshire",
        "Rapid hiring; licence sprawl; investor diligence on security posture.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 22,
            "active_mailboxes_measured": 31,
            "storage_tb_billed": 5,
            "storage_tb_used": 7.2,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 35,
            "active_sign_ins_30d": 30,
            "mfa_coverage_pct": 74,
            "unused_licences": 0,
            "hygiene": "Guest researchers on B2B collaboration; conditional access gaps.",
        },
        {
            "protected_tb": 12,
            "billed_tb": 11,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 20,
        },
        {
            "days_since_strategic_touch": 7,
            "stakeholder_count": 3,
            "last_qbr_days_ago": 30,
            "notes": "CTO wants ISO27001-lite narrative for Series A.",
        },
        {"missing_fields": ["lab_data_classification"], "confidence": "medium"},
        [
            ("Dr Emily Rao", "e.rao@redcliffe-bio.example.com"),
            ("Jonas Meier", "j.meier@redcliffe-bio.example.com"),
        ],
        [("open", "Lab instrument PC off-domain — exception request")],
        [("open", "Security baseline pack for investors", 0)],
        [],
        [
            ("executive", "Investor readiness: package MFA, guest access, backup immutability story."),
        ],
        [],
        (35, 42, 69),
    ),
    (
        "Stratford Theatre Trust",
        "active",
        "Arts / charity",
        "Stratford-upon-Avon, Warwickshire",
        "Marketing fit: cyber + continuity workshop for donor-facing systems.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 26,
            "active_mailboxes_measured": 25,
            "storage_tb_billed": 6,
            "storage_tb_used": 5.8,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 28,
            "active_sign_ins_30d": 24,
            "mfa_coverage_pct": 79,
            "unused_licences": 0,
            "hygiene": "Volunteer accounts need lifecycle policy.",
        },
        {
            "protected_tb": 11,
            "billed_tb": 11,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 200,
        },
        {
            "days_since_strategic_touch": 25,
            "stakeholder_count": 3,
            "last_qbr_days_ago": 140,
            "notes": "Fundraising team sensitive to donor data stories.",
        },
        {"missing_fields": ["volunteer_offboarding_policy"], "confidence": "medium"},
        [
            ("Laura Pemberton", "l.pemberton@stratford-theatre-trust.example.com"),
        ],
        [("open", "Box office Wi-Fi dropouts on performance nights")],
        [],
        [],
        [
            ("sales", "Event invite fit: donor data protection + continuity briefing for board."),
        ],
        [],
        (29, 33, 56),
    ),
    (
        "Thamesmead Logistics Hub Ltd",
        "watch",
        "Logistics / 3PL",
        "Dartford, Kent",
        "Low contact; single buyer; renewal in 6 months — concentration risk.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 140,
            "active_mailboxes_measured": 138,
            "storage_tb_billed": 30,
            "storage_tb_used": 31.5,
            "aged_debt_gbp": 2500,
            "invoice_friction": "minor_queries",
        },
        {
            "licensed_users": 145,
            "active_sign_ins_30d": 132,
            "mfa_coverage_pct": 86,
            "unused_licences": 0,
            "hygiene": "Generally fine; printer fleet aging.",
        },
        {
            "protected_tb": 58,
            "billed_tb": 57,
            "failed_jobs_7d": 1,
            "last_restore_test_days_ago": 90,
        },
        {
            "days_since_strategic_touch": 150,
            "stakeholder_count": 1,
            "last_qbr_days_ago": 300,
            "notes": "IT manager is sole contact for all decisions.",
        },
        {"missing_fields": ["secondary_buyer", "cfo_contact"], "confidence": "medium_low"},
        [
            ("Gareth Mills", "g.mills@thamesmead-logistics.example.com"),
        ],
        [("open", "Warehouse label printer driver pack conflict")],
        [],
        [],
        [
            ("executive", "Concentration risk: widen stakeholder map before renewal."),
        ],
        [],
        (48, 54, 46),
    ),
    (
        "Ulverston Foodservice Wholesale Ltd",
        "active",
        "Food wholesale",
        "Ulverston, Cumbria",
        "Healthy ops; minor backup job noise overnight — good contrast account.",
        {
            "source_sim": "sage",
            "currency": "GBP",
            "billed_m365_seats": 52,
            "active_mailboxes_measured": 51,
            "storage_tb_billed": 16,
            "storage_tb_used": 15.4,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 54,
            "active_sign_ins_30d": 50,
            "mfa_coverage_pct": 88,
            "unused_licences": 0,
            "hygiene": "No major issues.",
        },
        {
            "protected_tb": 31,
            "billed_tb": 31,
            "failed_jobs_7d": 1,
            "last_restore_test_days_ago": 35,
        },
        {
            "days_since_strategic_touch": 28,
            "stakeholder_count": 4,
            "last_qbr_days_ago": 100,
            "notes": "Family owners; pragmatic on spend.",
        },
        {"missing_fields": [], "confidence": "high"},
        [
            ("Hannah Irwin", "h.irwin@ulverston-food.example.com"),
        ],
        [("resolved", "Overnight backup warning — cleared as transient WAN blip")],
        [],
        [],
        [
            ("executive", "Stable account: use for baseline comparisons in portfolio reviews."),
        ],
        [],
        (20, 24, 55),
    ),
    (
        "Victoria Line Clinics Ltd",
        "at_risk",
        "Healthcare / private clinics",
        "London, Greater London",
        "Low contact + high churn risk: competitor circling; support-only relationship.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 74,
            "active_mailboxes_measured": 72,
            "storage_tb_billed": 13,
            "storage_tb_used": 13.8,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 78,
            "active_sign_ins_30d": 60,
            "mfa_coverage_pct": 66,
            "unused_licences": 2,
            "hygiene": "MFA fatigue on locum accounts; risky shared credentials reported once.",
        },
        {
            "protected_tb": 24,
            "billed_tb": 24,
            "failed_jobs_7d": 2,
            "last_restore_test_days_ago": 220,
        },
        {
            "days_since_strategic_touch": 180,
            "stakeholder_count": 2,
            "last_qbr_days_ago": 500,
            "notes": "Only helpdesk tickets; clinical director not engaged.",
        },
        {"missing_fields": ["clinical_director_mobile"], "confidence": "low"},
        [
            ("Rebecca Stone", "r.stone@victoria-line-clinics.example.com"),
        ],
        [
            ("open", "Locum cannot access EMR via MFA — recurring"),
            ("open", "Patient Wi-Fi portal complaints"),
        ],
        [],
        [("lost", "Lost: DR site refresh — competitor undercut", 3100000)],
        [
            ("executive", "Save risk: re-engage clinical director; competitor loss already signalled."),
            ("service", "Stabilise locum MFA pattern with approved device standard."),
        ],
        [],
        (86, 79, 20),
    ),
    (
        "Whitby Fisheries Cooperative",
        "active",
        "Food production",
        "Whitby, North Yorkshire",
        "Rural connectivity; seasonal staffing; marketing fit for continuity event.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 16,
            "active_mailboxes_measured": 15,
            "storage_tb_billed": 4,
            "storage_tb_used": 3.6,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 18,
            "active_sign_ins_30d": 14,
            "mfa_coverage_pct": 72,
            "unused_licences": 0,
            "hygiene": "Seasonal workers; temporary accounts need lifecycle.",
        },
        {
            "protected_tb": 8,
            "billed_tb": 8,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 100,
        },
        {
            "days_since_strategic_touch": 40,
            "stakeholder_count": 2,
            "last_qbr_days_ago": 200,
            "notes": "Owners care about weather + power outages affecting production.",
        },
        {"missing_fields": ["seasonal_worker_offboarding"], "confidence": "medium"},
        [
            ("Andrew Pike", "a.pike@whitby-fish-coop.example.com"),
        ],
        [("open", "4G failover flapping on production office router")],
        [],
        [],
        [
            ("sales", "Event fit: rural continuity + backup resilience workshop for coastal SMEs."),
        ],
        [],
        (33, 38, 49),
    ),
    (
        "Yare Valley Software Ltd",
        "active",
        "Technology / ISV",
        "Norwich, Norfolk",
        "Dev-heavy; GitHub + Azure; strong growth score; low risk.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 44,
            "active_mailboxes_measured": 44,
            "storage_tb_billed": 12,
            "storage_tb_used": 14.1,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 48,
            "active_sign_ins_30d": 46,
            "mfa_coverage_pct": 97,
            "unused_licences": 0,
            "hygiene": "Strong; optional GitHub Advanced Security cross-sell.",
        },
        {
            "protected_tb": 28,
            "billed_tb": 27,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 15,
        },
        {
            "days_since_strategic_touch": 10,
            "stakeholder_count": 5,
            "last_qbr_days_ago": 40,
            "notes": "CTO wants FinOps visibility on Azure spend (future connector).",
        },
        {"missing_fields": ["azure_cost_connector"], "confidence": "high"},
        [
            ("Daniel Okonkwo", "d.okonkwo@yare-valley-sw.example.com"),
            ("Sophie Allen", "s.allen@yare-valley-sw.example.com"),
        ],
        [("open", "Pipeline runner agents need new PAT rotation policy")],
        [("open", "GitHub Advanced Security evaluation", 360000)],
        [],
        [
            ("sales", "Growth: GHAS + secret scanning aligned to compliance narrative."),
        ],
        [],
        (16, 20, 84),
    ),
    (
        "Zetland Municipal Services JV",
        "watch",
        "Public sector JV",
        "Middlesbrough, North Yorkshire",
        "Data confidence test: conflicting contract vs PSA entitlement notes in demo_profile.",
        {
            "source_sim": "xero",
            "currency": "GBP",
            "billed_m365_seats": 190,
            "active_mailboxes_measured": 175,
            "storage_tb_billed": 40,
            "storage_tb_used": 39.0,
            "aged_debt_gbp": 0,
            "invoice_friction": "none",
        },
        {
            "licensed_users": 200,
            "active_sign_ins_30d": 168,
            "mfa_coverage_pct": 82,
            "unused_licences": 10,
            "hygiene": "OK; privileged access reviews overdue in policy doc (not in PSA).",
        },
        {
            "protected_tb": 80,
            "billed_tb": 80,
            "failed_jobs_7d": 0,
            "last_restore_test_days_ago": 50,
        },
        {
            "days_since_strategic_touch": 60,
            "stakeholder_count": 4,
            "last_qbr_days_ago": 190,
            "notes": "Joint venture governance slows decisions.",
        },
        {
            "missing_fields": ["privileged_access_review_owner"],
            "confidence": "medium",
            "conflicts": ["PSA contract SKU list does not match finance workbook v3 (demo)."],
        },
        [
            ("Clare Irving", "c.irving@zetland-msjv.example.com"),
            ("Michael Obi", "m.obi@zetland-msjv.example.com"),
        ],
        [("open", "Citrix ADC version mismatch after maintenance window")],
        [("open", "Privileged access review remediation", 0)],
        [],
        [
            ("executive", "Data confidence: reconcile PSA vs finance workbook before renewal committee."),
        ],
        [],
        (42, 46, 51),
    ),
]


def _more_accounts() -> list[tuple[Any, ...]]:
    """Additional synthetic accounts to reach 24+ customers with varied patterns."""
    extra_names = [
        ("Coastal Wind LLP", "active", "Energy / consulting", "Llandudno, Conwy", "Small healthy professional services."),
        ("Derwent Precision Optics Ltd", "watch", "Manufacturing", "Derby, Derbyshire", "Opportunity: modern workplace for lab PCs."),
        ("Fairhaven Care Homes Ltd", "at_risk", "Healthcare / care homes", "Southport, Merseyside", "Thin night-shift coverage; backup alerts ignored."),
        ("Granite City Accountants LLP", "active", "Professional services", "Aberdeen, Scotland", "Clean M365; strong relationship; reference for billing integrity."),
        ("Highfield Agricultural Co-op", "watch", "Agriculture", "Salisbury, Wiltshire", "Seasonal workers; mobile device compliance gaps."),
        ("Ironbridge Industrial Sensors Ltd", "active", "Industrial IoT", "Telford, Shropshire", "OT edge devices; backup immutability interest."),
    ]
    rows: list[tuple[Any, ...]] = []
    for i, (name, status, ind, city, note) in enumerate(extra_names):
        rows.append(
            (
                name,
                status,
                ind,
                city,
                note,
                {
                    "source_sim": "xero" if i % 2 == 0 else "sage",
                    "currency": "GBP",
                    "billed_m365_seats": 20 + i * 3,
                    "active_mailboxes_measured": 19 + i * 3,
                    "storage_tb_billed": 5 + i,
                    "storage_tb_used": 5.1 + i * 0.2,
                    "aged_debt_gbp": 500 if status == "at_risk" else 0,
                    "invoice_friction": "minor_queries" if status == "at_risk" else "none",
                },
                {
                    "licensed_users": 24 + i * 3,
                    "active_sign_ins_30d": 20 + i * 2,
                    "mfa_coverage_pct": 60 + i * 5,
                    "unused_licences": i % 3,
                    "hygiene": "Synthetic baseline for demo portfolio spread.",
                },
                {
                    "protected_tb": 10 + i,
                    "billed_tb": 9 + i,
                    "failed_jobs_7d": 2 if status == "at_risk" else 0,
                    "last_restore_test_days_ago": 80 + i * 10,
                },
                {
                    "days_since_strategic_touch": 20 + i * 11,
                    "stakeholder_count": 2 + (i % 3),
                    "last_qbr_days_ago": 90 + i * 20,
                    "notes": "Synthetic UK MSP demo account — not a real business.",
                },
                {"missing_fields": [] if status == "active" else ["secondary_contact"], "confidence": "high" if status == "active" else "medium"},
                [(f"Contact {i + 1}", f"user{i + 1}@demo-extra-msp.example.com")],
                [("open", f"Synthetic ticket {i+1}: endpoint health check follow-up")] if status != "active" else [],
                [("open", f"Synthetic opportunity {i+1}", 150000 + i * 50000)] if i % 2 == 0 else [],
                [("draft", f"Synthetic quote draft {i+1}", 90000 + i * 10000)] if i % 3 == 0 else [],
                [
                    (
                        "executive",
                        "Synthetic recommendation: review demo_profile billing vs M365 for this account.",
                    )
                ],
                [],
                (25 + i * 3, 28 + i * 2, 50 + i),
            )
        )
    return rows


ALL_ACCOUNT_SPECS = ACCOUNT_SPECS + _more_accounts()


def _clear_tenant_workspace(db: Session, tenant_id: UUID) -> None:
    db.execute(delete(AITaskRun).where(AITaskRun.tenant_id == tenant_id))
    db.execute(delete(Recommendation).where(Recommendation.tenant_id == tenant_id))
    db.execute(delete(Action).where(Action.tenant_id == tenant_id))
    db.execute(delete(AccountScore).where(AccountScore.tenant_id == tenant_id))
    db.execute(delete(Ticket).where(Ticket.tenant_id == tenant_id))
    db.execute(delete(Opportunity).where(Opportunity.tenant_id == tenant_id))
    db.execute(delete(Quote).where(Quote.tenant_id == tenant_id))
    db.execute(delete(Contact).where(Contact.tenant_id == tenant_id))
    db.execute(delete(SourceEntityMapping).where(SourceEntityMapping.tenant_id == tenant_id))
    db.execute(delete(IntegrationSyncRun).where(IntegrationSyncRun.tenant_id == tenant_id))
    db.execute(delete(Customer).where(Customer.tenant_id == tenant_id))
    db.execute(delete(SourceSystemConnection).where(SourceSystemConnection.tenant_id == tenant_id))
    db.flush()


def _seed_connectors_and_sync(db: Session, tenant_id: UUID) -> list[SourceSystemConnection]:
    """Simulated multi-vendor footprint (no live APIs)."""
    now = datetime.now(UTC)
    specs = [
        ("autotask", "Autotask PSA (demo simulation)", "psa"),
        ("connectwise", "ConnectWise Manage (legacy label)", "psa"),
        ("itquoter", "ITQuoter (demo simulation)", "quoting"),
        ("veeam", "Veeam Backup & Replication (demo simulation)", "backup"),
        ("microsoft_365", "Microsoft 365 / Entra (demo simulation)", "productivity"),
        ("xero", "Xero (demo simulation)", "finance"),
        ("sage", "Sage Intacct-style (demo simulation)", "finance"),
    ]
    conns: list[SourceSystemConnection] = []
    for system_type, label, _ in specs:
        c = SourceSystemConnection(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            system_type=system_type,
            provider_family="generic",
            display_name=label,
            status="configured",
            health_status="healthy",
            is_enabled=True,
            last_successful_sync_at=now - timedelta(hours=2 + len(conns)),
            last_sync_at=now - timedelta(hours=1),
            sync_cadence_minutes=120,
        )
        db.add(c)
        conns.append(c)
    db.flush()
    for c in conns:
        run = IntegrationSyncRun(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            source_connection_id=c.id,
            trigger_mode="scheduled",
            status="succeeded",
            records_processed=120 + hash(str(c.id)) % 400,
            started_at=now - timedelta(minutes=45),
            completed_at=now - timedelta(minutes=44),
            stats_json={"demo": True, "entities": "customers,contacts,tickets,opportunities,quotes"},
        )
        db.add(run)
    for c in conns:
        if c.system_type == "xero":
            c.encrypted_config = encrypt_settings_payload({"demo_mode": True})
            c.auth_mode = "sandbox"
        if c.system_type == "microsoft_365":
            c.base_url = "http://connector-lab:8099"
            c.auth_mode = "oauth2"
            c.encrypted_config = encrypt_settings_payload(
                {
                    "tenant_id": "demo-msp",
                    "client_id": "connector-lab-demo-client",
                    "client_secret": "connector-lab-demo-secret",
                    "token": "connector-lab-dev-token",
                }
            )
    db.flush()
    return conns


def replace_demo_tenant_workspace(db: Session, tenant_id: UUID) -> int:
    """Wipe and rebuild canonical demo workspace rows. Returns customer count."""
    _clear_tenant_workspace(db, tenant_id)
    conns = _seed_connectors_and_sync(db, tenant_id)
    conn_by_type = {c.system_type: c for c in conns}
    psa = conn_by_type.get("autotask") or conns[0]
    n = 0
    for idx, spec in enumerate(ALL_ACCOUNT_SPECS):
        (
            name,
            status,
            industry,
            city_line,
            scenario_note,
            billing,
            m365,
            backup,
            rel,
            dq,
            contacts,
            tickets,
            opps,
            quotes,
            recs,
            actions,
            scores,
        ) = spec
        owner = OWNERS[idx % len(OWNERS)]
        ext = f"AT-UK-{idx+1:04d}"
        profile = _demo_profile(
            industry=industry,
            city_line=city_line,
            billing=billing,
            microsoft_365=m365,
            backup=backup,
            relationship=rel,
            data_quality=dq,
            scenario_note=scenario_note,
        )
        cust = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            status=status,
            owner_name=owner,
            external_ref=ext,
            demo_profile=profile,
        )
        db.add(cust)
        db.flush()
        xero_conn = conn_by_type.get("xero")
        upsert_finance_for_customer(
            db,
            tenant_id=tenant_id,
            customer_id=cust.id,
            customer_name=name,
            demo_profile=profile,
            source_connection_id=xero_conn.id if xero_conn else None,
            provenance="demo_seed",
        )
        db.add(
            SourceEntityMapping(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                source_connection_id=psa.id,
                entity_type="customer",
                source_id=ext,
                canonical_entity_id=cust.id,
                mapping_metadata={"demo_seed": True},
            )
        )
        for cn, em in contacts:
            db.add(Contact(id=uuid.uuid4(), tenant_id=tenant_id, customer_id=cust.id, name=cn, email=em, external_ref=f"{ext}-C-{cn[:6]}"))
        for tst, subj in tickets:
            db.add(
                Ticket(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    customer_id=cust.id,
                    status=tst,
                    subject=subj[:240],
                    external_ref=f"{ext}-T-{uuid.uuid4().hex[:8]}",
                )
            )
        for ost, title, cents in opps:
            db.add(
                Opportunity(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    customer_id=cust.id,
                    status=ost,
                    title=title[:200] if title else None,
                    value_cents=cents,
                    external_ref=f"{ext}-O-{uuid.uuid4().hex[:8]}",
                )
            )
        for qst, title, cents in quotes:
            db.add(
                Quote(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    customer_id=cust.id,
                    status=qst,
                    title=title[:200] if title else None,
                    value_cents=cents,
                    source_system="itquoter" if (title and "quote" in title.lower()) else "autotask",
                    external_ref=f"{ext}-Q-{uuid.uuid4().hex[:8]}",
                )
            )
        for scope, summary in recs:
            s = summary[:278] if len(summary) > 278 else summary
            db.add(
                Recommendation(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    customer_id=cust.id,
                    scope=scope,
                    status="open",
                    summary=s,
                )
            )
        for desc in actions:
            db.add(Action(id=uuid.uuid4(), tenant_id=tenant_id, customer_id=cust.id, description=desc[:278]))
        r, a, g = scores
        db.add(AccountScore(id=uuid.uuid4(), tenant_id=tenant_id, customer_id=cust.id, risk_score=r, attention_score=a, growth_score=g))
        n += 1
    db.flush()
    return n


def seed_demo_workspace_if_demo_tenant(db: Session, tenant: Tenant | None) -> int:
    """If tenant is the demo MSP slug, replace workspace data."""
    if tenant is None or tenant.slug != DEMO_TENANT_SLUG:
        return 0
    return replace_demo_tenant_workspace(db, tenant.id)
