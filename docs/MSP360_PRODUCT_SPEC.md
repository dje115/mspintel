# Master product specification — mspintel

**Status:** Living document — authoritative for **intended product direction**.  
**Codebase name:** `mspintel` (repository, APIs, UI branding).  
**File name:** `MSP360_PRODUCT_SPEC` reflects **360°** coverage of customer, commercial, service, marketing, finance, and operations intelligence—not a separate product rename.

**Companion docs:** [CURSOR_RULES.md](CURSOR_RULES.md) (implementation discipline), [DATA_INGESTION_AND_WAREHOUSE.md](DATA_INGESTION_AND_WAREHOUSE.md), [AI_CONFIGURATION_AND_PROMPTS.md](AI_CONFIGURATION_AND_PROMPTS.md), [ROUTES_UX_MAP.md](ROUTES_UX_MAP.md), [TENANT_PRODUCT_WIREFRAMES.md](TENANT_PRODUCT_WIREFRAMES.md).

---

## 1. Product vision

`mspintel` is evolving from an MSP **dashboard** into a **tenant-scoped MSP customer intelligence and operating platform**: a single place where service, sales, marketing, finance/revenue assurance, and operations align on **one customer truth**, backed by **connector-driven ingestion**, a **canonical internal model**, and **auditable, prompt-driven AI**.

### 1.1 What the platform should help an MSP do

| Outcome | Description |
|--------|--------------|
| **Retain** | Spot risk earlier; run save-the-account and relationship-repair workflows; prove value before renewal. |
| **Serve** | Improve delivery quality, reduce repeat incidents, surface stalled remediation and handoff failures. |
| **Grow commercially** | Reopen lost quotes, unstick pipeline, detect leakage and underbilling, align contract footprint to delivery. |
| **Engage professionally** | Account manager cadence, QBR/review prep, next conversation and talk-track guidance, event/campaign matching. |
| **Trust the data** | Explicit confidence, blind spots, and “what we cannot conclude yet” when sources are missing or stale. |
| **Use AI safely** | Provider/model routing per tenant; prompts from registry where applicable; lineage on every run (`ai_task_runs`). |

### 1.2 Systems in scope (over time)

PSA (**Autotask**, **ConnectWise**), quoting (**ITQuoter**), backup (**Veeam** and peers), **Microsoft 365 / Entra / Azure**, accounting (**Xero**, **Sage**), telephony (**3CX**, CDR), future **RMM**, **documentation**, **CRM**, **procurement**, **security** tooling—ingested via **tenant-scoped connectors** into a **canonical model**, not ad-hoc per-page integrations.

---

## 2. Core product principles

| Principle | Meaning for implementation |
|-----------|----------------------------|
| **Tenant-scoped & secure** | Data, connectors, prompts, and AI routes are tenant-bound; platform admin is a separate surface and JWT scope. |
| **Docker-first** | Local and CI assume Compose; see [CURSOR_RULES.md](CURSOR_RULES.md). |
| **Auditable AI** | Every production AI call should be traceable: provider family, model, prompt definition/version, fallbacks, outcome. |
| **Prompt/version-driven** | Prefer **prompt DB** (`prompt_key` + versions) over hardcoded strings for user-facing analysis templates. |
| **Connector-driven ingestion** | Product signals come from sync runs and mappings, not manual CSV uploads as the primary path. |
| **Canonical internal model** | Source entities map to shared tenant tables; PSA-specific shapes stay in adapter boundaries. |
| **Warehouse-ready** | Current-state operational store first; append-only snapshots/analytics layer later without re-architecture. |
| **Tenant UX is the hero** | `/app/...` gets polish and IA priority; `/platform/...` stays visually distinct (operator tooling). |
| **Human in the loop** | AI proposes, explains, drafts; humans accept, edit, and own customer outcomes. |
| **Action over vanity** | Prefer queues, next actions, and remediation workflows over static charts alone. |
| **Honest uncertainty** | Surfaces confidence, missing fields, and stale sync—never silent guessing when data is insufficient. |
| **Persistent derived knowledge** | Tenant-scoped **knowledge objects** (summaries, narratives, posture) maintained between syncs—not only ad hoc RAG or one-off model output; see **Persistent tenant knowledge layer** below. |

---

## Persistent tenant knowledge layer (AI-maintained MSP knowledge base)

`mspintel` must not rely **only** on ad hoc **query-time** synthesis (e.g. repeated “explain this account” over raw rows) or **raw RAG** over synced records as the long-term product model. The platform should maintain a **persistent, tenant-scoped knowledge layer**: **derived knowledge objects** that sit **between** canonical operational data and user-facing surfaces (360, QBR prep, marketing, billing integrity, AM guidance).

### Why this layer exists

| Without persistent knowledge | With persistent knowledge |
|-------------------------------|---------------------------|
| Every UI or AI call re-synthesises from scratch | **Stable narratives** and summaries can be **refreshed on a schedule** or after major syncs |
| Hard to compare “what we believed last week” vs today | **Versioned refresh** tied to prompts and `ai_task_runs` lineage |
| Raw RAG can drift or omit governance | **Governed prompts**, staleness flags, and **evidence pointers** back to canonical rows |
| Dashboards alone lack narrative glue | Product areas share **reusable objects** instead of duplicating LLM work |

**Source systems** (PSA, backup, M365, etc.) remain the **source of truth** for facts. **Canonical operational entities** remain the **system of record** for current-state CRM/service/commercial rows. **Knowledge objects** are **derived**: they interpret, summarise, and connect—never replace—those layers.

### Four-layer data & knowledge model

| Layer | What it is | Examples in `mspintel` terms |
|-------|------------|------------------------------|
| **1. Raw / synced source** | Payloads and shapes as ingested from connectors; mapping to external IDs | Adapter inputs, sync payloads, `source_entity_mappings` |
| **2. Canonical operational** | Normalised tenant tables used for queues, 360 tables, APIs | `customers`, `tickets`, `opportunities`, `quotes`, … |
| **3. Derived knowledge objects** | **Persistent**, refreshable summaries/narratives/postures per account (or tenant segment) with lineage | `customer_overview`, `relationship_health`, `billing_integrity` (concepts—not yet all implemented) |
| **4. Historical / warehouse / analytics** | Append-only facts and trends for reporting | Future snapshot facts, event streams |

Product and AI features should **prefer reading layer 3** when a suitable object exists, and **write/refres**h it via **maintainer** flows rather than re-synthesising blindly on every page load.

### Example knowledge object types

Each type is a **logical** object (future storage may be one table or several). For each: **meaning** · **product consumers** · **feeds** · **prompt families**.

| Type | Represents | Used by | Typical feeds | Prompts (illustrative) |
|------|------------|---------|---------------|------------------------|
| `customer_overview` | Account-level executive narrative | Dashboard hints, 360 header, exec briefings | Canonical customer + scores + recs | Maintainer + `account_summary`-class |
| `relationship_health` | Stakeholder coverage, touch cadence, strategic vs support-only | 360, relationship workspace, QBR, marketing fit | Contacts, tickets, meetings, CDR (later) | Maintainer + `relationship_health_summary` |
| `billing_integrity` | Variance, leakage, underbilling hypotheses (not invoices) | Revenue assurance, 360 finance strip | PSA contracts/usage, Xero/Sage (later) | Maintainer + `billing_variance_summary` |
| `m365_hygiene` | Licence and posture snapshot | M365 health, 360 technical | Graph / Entra (later) | Maintainer + `m365_hygiene_summary` |
| `backup_posture` | Protection coverage, job health, gaps | Service risk, backup billing, events | Veeam (later) | Maintainer + `backup_risk_summary` |
| `stalled_work` | Cross-entity stall narrative (quotes/projects/installs) | Stalled work queue, AM guidance | PSA projects, tickets | Maintainer + `stalled_work_*` |
| `qbr_prep` | Rolling QBR pack inputs beyond one-off agenda | Review prep workspace | Maintainer output + calendar (later) | Maintainer + `customer_review_agenda` |
| `marketing_fit` | Segment/event fit signals per account | Campaign matching, event ideas | Segments + backup/M365 posture | Maintainer + `campaign_customer_matching` |
| `account_confidence` | What we can/cannot conclude; missing sources | Data quality, 360 blind-spots panel | Sync coverage, field presence | Maintainer + `data_gap_summary` / `account_confidence_explanation` |
| `risk_summary` | Consolidated risk narrative (may complement scores) | At-risk, 360, save-the-account | Scores, tickets, recs | Maintainer + `risk_summary` |
| `opportunity_summary` | Commercial narrative | 360 pipeline strip, marketing | Opps, quotes | Maintainer + `opportunity_detection` |
| `service_summary` | Delivery pressure narrative | 360, QBR | Tickets, SLA signals | Maintainer + ticket/service prompts |

### Maintenance lifecycle (high level)

Knowledge objects are **not static**:

- **Created** when first refresh runs (or when a new account gains minimum data).
- **Refreshed** on cadence, after **significant sync completion**, or on **manual “rebuild knowledge”** (future).
- **Marked stale** when upstream canonical data changes beyond a threshold, or when **prompt version** changes require re-derivation.
- **Re-derived** after major connector backfills; optionally **linted** for contradictions vs canonical facts or missing mandatory links.
- **Regenerated** when operators activate a new **prompt version** for the maintainer key (policy: optional batch job).

### Three recurring operations (mspintel terms)

1. **Ingest / update** — connector sync updates canonical rows → triggers **staleness** or **queued refresh** for affected knowledge objects.  
2. **Query / use** — Customer 360, QBR prep, marketing matching, AM guidance, billing UI **read** the latest valid object + show **freshness** and **confidence**.  
3. **Lint / check** — jobs or on-read checks flag **stale**, **low-confidence**, or **evidence-drifting** objects; surface in data quality and admin surfaces.

### Evidence, confidence, and lineage

Each stored object (when implemented) should carry where practical:

- **Evidence** — references to canonical row IDs / entity types / last sync run id (not raw secrets).  
- **Prompt** — `prompt_key`, `prompt_version_id` used for the **maintainer** or last refresh.  
- **Model lineage** — provider family, model; align with **`ai_task_runs`** for the refresh execution.  
- **Freshness** — `derived_at`, `valid_until` or `stale_after_sync_seq` pattern (TBD at implementation).  
- **Confidence / gaps** — structured “cannot conclude X without Y” notes for honest UX.

This aligns with existing **prompt versioning** and **`ai_task_runs`** lineage; maintainer runs are first-class `ai_task_runs` (or linked child runs) in implementation.

### Product area mapping (read path)

- **Customer 360** — eventually composes from **knowledge objects** for overview, risk, relationship, data confidence, billing posture, technical posture—not only live queries.  
- **QBR / review prep** — consumes `qbr_prep`, `relationship_health`, `risk_summary`, `opportunity_summary`, `billing_integrity`, `account_confidence` (where present) plus one-off agenda generation.  
- **Marketing / campaign matching** — uses `marketing_fit`, `relationship_health`, `opportunity_summary`, `backup_posture`, `m365_hygiene`, `service_summary` to rank invites and segments.  
- **Account manager guidance** — prefers **maintained** account narratives + next-step objects over only ephemeral LLM calls.  
- **Billing integrity** — persistent `billing_integrity` objects for variance, leakage, remediation narrative, confidence.  
- **Data confidence** — `account_confidence` (and related) as **maintained** artefacts, not only a single numeric score.

### Maintainer prompts (knowledge object refresh)

These are **not** the same as one-off user-facing answers: they **write or refresh** layer-3 objects under governance. Planned **stable key** examples (names may be refined at implementation):

| Maintainer key | Refreshes (conceptual object) |
|----------------|-------------------------------|
| `customer_overview_maintainer.system` | `customer_overview` |
| `relationship_health_maintainer.system` | `relationship_health` |
| `billing_integrity_maintainer.system` | `billing_integrity` |
| `m365_hygiene_maintainer.system` | `m365_hygiene` |
| `backup_posture_maintainer.system` | `backup_posture` |
| `qbr_prep_maintainer.system` | `qbr_prep` |
| `data_confidence_maintainer.system` | `account_confidence` / coverage narrative |
| `marketing_fit_maintainer.system` | `marketing_fit` |
| `stalled_work_maintainer.system` | `stalled_work` |
| `risk_summary_maintainer.system` | `risk_summary` |
| `opportunity_summary_maintainer.system` | `opportunity_summary` |
| `service_summary_maintainer.system` | `service_summary` |

**Relationship to user-facing keys:** e.g. `account_manager_next_conversation.system` may **read** `customer_overview` + `relationship_health` + fresh canonical slices; `billing_variance_summary.system` may read **`billing_integrity`** object + live numbers; `marketing_event_idea_generation.system` may read **`marketing_fit`**. Maintainer prompts run on **schedules or triggers**; user-facing prompts run on **demand** or UI actions.

---

## 3. User roles and perspectives

For each role: **goals** → **primary sections** → **signals** → **AI-assisted outputs** → **success in product**.

| Role | Goals | Primary sections | Key signals | AI outputs (examples) | Success looks like |
|------|-------|------------------|-------------|------------------------|---------------------|
| **Platform admin** | Operate multi-tenant SaaS safely | `/platform/*` | Tenant health, AI run tails, MFA policy | N/A for tenant prompts | Stable tenants, secure operators |
| **Tenant admin** | Configure org, connectors, AI, members | Integrations, AI engines, Prompts, Members, Security | Sync health, prompt drift, session risk | Config summaries, policy explanations | Reliable onboarding and governance |
| **Director / owner** | Portfolio risk & growth | Dashboard, At-risk, Commercial, Data quality | Risk counts, lost quotes, margin pressure | Executive summaries, trend explanations | Fewer surprise churns; clearer priorities |
| **Account manager** | Relationship & revenue per account | Customers, 360, Recommendations, **AM workspace** (planned) | Low touch, single stakeholder, no QBR | Next conversation, talk track, review agenda | Cadence executed; revenue protected |
| **Sales / commercial** | Pipeline & quotes | Opportunities, Marketing, Win-back (planned) | Stalled opps, lost quotes, dormant SKUs | Reactivation copy, next-best commercial | Pipeline velocity; win-backs logged |
| **Service manager** | Delivery & risk | Service risk, Needs attention, Tickets context | Open tickets, repeat issues, SLA | Risk explanations, stalled work next action | Fewer escalations; proactive fixes |
| **Marketing** | Campaigns & events | Marketing, **Event ideas / matching** (planned) | Segment fit, licence/backup themes | Event ideas, invite drafts, segment summaries | Qualified invites; less generic blast |
| **Finance / revenue assurance** | Billing integrity | **Billing / revenue assurance** (planned), Customers | Billed vs actual, uninvoiced acceptance | Variance summaries, remediation steps | Margin protected; fewer write-offs |
| **Operations / delivery lead** | Handoffs & stalled work | Recommendations, **Stalled work** (planned) | Stalled projects/installs/onboarding | Handoff failure explanations | Clear ownership and dates |
| **Technical specialist (later)** | M365, backup, security depth | **M365 health**, **Backup** depth, Security posture (planned) | Licence gaps, job failures, posture | Hygiene summaries, upsell opportunities | Technical debt visible and sold |
| **Customer success (later)** | Relationship-focused health | Relationship health, Engagement plan (planned) | Engagement trend, exec coverage | Save-plan narrative, QBR recovery | Health scores improving |

---

## 4. Product section matrix (summary)

Columns: **section** · **purpose** · **key users** · **core data sources** · **AI prompt keys (representative)** · **maturity now** · **next likely phase**.

| Section | Purpose | Key users | Core data sources | Prompt keys (examples) | Maturity | Next phase |
|---------|---------|-----------|-------------------|-------------------------|----------|------------|
| Dashboard | “What needs attention today?” | Director, AM, Service | Canonical customers, recs, commercial, service-risk API | *(mostly aggregated; future exec summary)* | **Existing** | Richer widgets per roadmap |
| Customers / directory | Account list & filters | All | `customers`, scores | — | **Existing** | Saved views, bulk assign |
| Customer 360 | Cross-system one account | AM, Sales, Service | Canonical rows + AI endpoints; **future:** persisted **knowledge objects** (overview, posture, confidence) | `account_summary`, `risk_summary`, `churn_explanation`, `recommendation_explanation` + maintainer keys (see §20.7) | **Existing / partial** | M365, backup, billing panels; knowledge-layer reads |
| Recommendations | Cross-account queue | Service, AM, Ops | `recommendations` | `recommendation_explanation` | **Existing** | More task types |
| Opportunities & quotes | Pipeline & lost | Sales | PSA opps/quotes | `opportunity_detection`, `lost_quote_reactivation` | **Existing** | ITQuoter-native signals |
| At-risk | Risk operating list | Director, Service | Customer status/scores | `churn_explanation`, `risk_summary` | **Existing** | Deeper PSA+RMM signals |
| Needs attention | Watch list | AM, Service | Customer status | `risk_summary` | **Existing** | Same |
| Service risk | Backup + delivery snapshot | Service | Tickets + backup placeholder | `backup_risk_summary`, `stalled_work_explanation` | **Partial** | Veeam connector |
| Backup & recovery | Protection posture | Service, Technical | Backup jobs, workloads | `backup_gap_opportunity`, `backup_event_matching` | **Future** | Veeam + billing correlation |
| Reviews / QBR prep | Review cadence | AM, Director | Customer detail API + meetings (later) | `customer_review_agenda.system`, AM guidance keys | **Partial** (full prep workspace + `?customer_id=`; agenda AI later) | Calendar + CRM + autosave notes |
| Members | Team & invites | Admin | Memberships | — | **Existing** | SSO |
| Integrations | Connectors | Admin | Connections, sync runs | — | **Existing** | CW, ITQuoter, Veeam, M365… |
| AI engines | Provider routing | Admin | `ai_providers`, routes | — | **Existing** | More adapters |
| Prompts | Overrides & versions | Admin | `prompt_definitions`, versions | — | **Existing** | More keys from §20 |
| Security | Sessions | All users | Sessions | — | **Existing** | SSO |
| Onboarding | First-run | Admin | Onboarding state | — | **Existing** | Connector wizard |
| Data quality / gaps | Freshness & coverage | Ops, Admin | Sync runs, mapping density | `data_gap_summary`, `account_confidence_explanation` | **Wireframed** | Per-entity coverage scores |
| Stalled work | Quotes/projects/installs stuck | Ops, Sales, Service | PSA projects, tickets, quotes | `stalled_work_explanation`, `stalled_work_next_action` | **Planned** | PSA project entities |
| Relationship health | Exec coverage, touch | AM | Contacts, activities (telephony later) | `relationship_health_summary`, `stakeholder_gap_explanation` | **Planned** | Activity ingestion |
| AM workspace / next conversation | Cadence & talk track | AM | 360 + recs + commercial | `account_manager_next_conversation`, `account_manager_call_script` | **Planned** | Prompt + UI bundle |
| Retention / save-the-account | Rescue workflows | AM, Director | At-risk + playbooks | `churn_explanation` + save-plan templates | **Planned** | Workflow state machine |
| Win-back / lost customer | Recover dormant revenue | Sales, Marketing | Lost quotes, dormant accounts | `lost_quote_reactivation`, `campaign_customer_matching` | **Partial** | Campaign execution |
| Revenue assurance / billing | Margin & leakage | Finance | PSA contracts, usage (later Xero) | `billing_variance_summary`, `revenue_leakage_explanation` | **Planned** | Accounting connectors |
| M365 health & licences | Hygiene & upsell | Technical, AM | Graph/Entra (later) | `m365_hygiene_summary`, `m365_upsell_opportunity` | **Future** | Microsoft connector |
| Marketing & campaigns | Growth programmes | Marketing | Customers, segments | `marketing_event_idea_generation`, `event_invite_draft`, `campaign_customer_matching` | **Partial** (segments, event board, matching placeholders) | Idea bank DB + live matching |
| Telephony / 3CX | Call relationship context | AM | CDR (later) | `relationship_health_summary` (augmented) | **Future** | CDR connector |
| Security posture | Tenant customer security overview | Technical | EDR/M365 (later) | `technical_gap_summary` | **Future** | Security vendor APIs |
| Procurement / install flow | Order→install visibility | Ops | PSA procurement (later) | `stalled_work_explanation` | **Future** | Deeper PSA |

---

## 5. Tenant-facing sections — detail

### 5.1 Core operational (existing routes)

- **Dashboard (`/app`)** — KPIs, priority lists, deep links into workspaces. *Widgets:* executive row, at-risk/attention panels, service-risk teaser. *Actions:* click-through to queues and accounts. *Maturity:* existing.
- **Customers & Customer 360** — Directory + tabs (overview, recs, pipeline, activity). *AI:* account summary, risk, churn, recommendation explain. *Direction:* panels should increasingly consume **maintained tenant knowledge objects** (see **Persistent tenant knowledge layer**) rather than only live synthesis. *Maturity:* existing; enrichment planned per §16.
- **Reviews & QBR prep (`/app/reviews`)** — Agenda and AM guidance today; *target:* combine one-off prompts with **maintained** objects such as `qbr_prep`, `relationship_health`, `risk_summary`, `billing_integrity`, `account_confidence` when the knowledge layer is implemented.
- **Recommendations / Opportunities / At-risk / Attention / Service risk** — As implemented; see wireframes. *Maturity:* existing / service-risk backup area placeholder.

### 5.2 Expanded retention, commercial, care (planned unless noted)

Each row: **purpose** · **widgets** · **actions** · **signals** · **sources** · **prompts** · **maturity**.

**Stalled work** — Detect stuck quotes, orders, installs, projects, onboarding, remediation, QBR follow-ups, procurement handoffs, “accepted not started,” internal handoff failures. *Widgets:* queue by stall type, aging, owner. *Actions:* assign, snooze, open 360. *Signals:* stage age, no activity, SLA breach. *Sources:* PSA projects, tickets, quotes. *Prompts:* `stalled_work_explanation`, `stalled_work_next_action`. *Maturity:* **planned**.

**Low-contact / relationship health** — Support-only relationship, single stakeholder, missing DM, no QBR, weak AM cadence, optional call volume. *Widgets:* health score, stakeholder map, timeline. *Actions:* schedule QBR, add contact, assign AM. *Sources:* tickets, meetings, CDR (later). *Prompts:* `relationship_health_summary`, `stakeholder_gap_explanation`. *Maturity:* **planned**.

**Customer engagement plan** — Coordinated touches across sales/service/marketing. *Maturity:* **future**.

**Account manager workspace / next conversation** — “What next,” 3-bullet talk track, customer-friendly issue framing, meeting agenda, repair vs commercial angles, event invite. *Prompts:* `account_manager_next_conversation`, `account_manager_call_script`, `next_best_commercial_conversation`. *Maturity:* **planned**.

**Retention / save-the-account** — Playbooks for declining engagement, frustration, stalled projects, recurring issues, rising ticket load, no strategic contact, no review, weak adoption, commercial stagnation. *Prompts:* `churn_explanation`, save-plan narrative (keyed variant of account manager family). *Maturity:* **planned**.

**Win-back / lost customer / lost commercial** — Lost quotes, stalled opps, dormant “used to buy X,” backup/security reopeners, targeted campaigns, event matching. *Prompts:* `lost_quote_reactivation`, `campaign_customer_matching`, `marketing_event_idea_generation`. *Maturity:* **partial** (lost quotes UI exists).

**Revenue assurance / billing checks** — Users vs billed, mailboxes, backup storage/workloads, active uninvoiced services, under/overbilling, contract vs delivery footprint; later Xero/Sage reconciliation. *Prompts:* `billing_variance_summary`, `revenue_leakage_explanation`, `billing_remediation_next_action`, `underbilling_opportunity`. *Direction:* persistent **`billing_integrity`** (and related) knowledge objects for variance, leakage, remediation path, and confidence—see knowledge layer. *Maturity:* **planned**.

**Microsoft 365 health & licence optimisation** — Unused/stale users, licence mismatch, MFA posture (later), Teams/SP governance (later), billing vs usage. *Prompts:* `m365_hygiene_summary`, `m365_upsell_opportunity`. *Maturity:* **future** (connector).

**Backup billing & protection** — Coverage gaps, failed/stale jobs, restore-test gaps, unprotected workloads, storage vs billed, recovery readiness, workshop/event ideas. *Prompts:* `backup_risk_summary`, `backup_gap_opportunity`, `backup_event_matching`. *Maturity:* **future**.

**Marketing / events / campaigns** — Idea capture, AI refinement, customer→event matching, segments, invite copy, nurture, review invites, cyber/continuity/AI event themes. *Prompts:* `marketing_event_idea_generation`, `marketing_idea_refinement`, `campaign_segment_summary`, `event_invite_draft`. *Direction:* matching should use **persistent** objects such as `marketing_fit`, `relationship_health`, `backup_posture`, `m365_hygiene`, `service_summary`, `opportunity_summary` when available. *Maturity:* **partial** (marketing shell).

**Telephony / 3CX** — Relationship and AM cadence from call patterns. *Maturity:* **future**.

**Finance intelligence** — Cross-view of commercial + accounting signals. *Maturity:* **future**.

**Documentation / coverage quality** — Link coverage to risk and QBR. *Maturity:* **future**.

**Security posture / compliance overview** — Tenant-customer security narrative. *Maturity:* **future**.

---

## 6. Customer retention, at-risk, save-the-account

**Detection inputs:** engagement trend (tickets, meetings, marketing responses), sentiment proxies (repeat issues, escalations), project stall flags, commercial dormancy, review/QBR recency, stakeholder breadth, backup/M365 adoption vs contracted, data confidence flags.

**Product behaviours:** ranked save queue; **save plan** doc per account (tasks, owners, dates); **next conversation** card with tone guidance; **event/campaign** suggestions tied to account segment; **QBR recovery** path when review overdue.

**Guardrails:** Always show **why** we believe risk (drivers + confidence). Offer **human override** and audit of playbook steps completed.

---

## 7. Win-back, lost commercial, drifting customers

**Signals:** lost-quote age and value, stalled high-value opps, dormant services, SKU drop-off, former high-touch accounts gone quiet, unclaimed renewal windows.

**Outputs:** ranked win-back list; **one-click** draft outreach (prompt-driven, editable); **campaign bundles** (segment + copy + owner); match accounts to **event themes** (e.g. backup workshop for unprotected workloads—once data exists).

---

## 8. Relationship health, low-contact, stakeholder coverage

**Detect:** no contact in N days; only support tickets; single known contact; no labelled economic buyer; no QBR in M months; AM task backlog; optional **low outbound call volume** vs peers once telephony exists.

**Surfaces:** relationship score; stakeholder map; **gap explanation** AI with honest “missing telephony data” caveats.

---

## 9. Stalled pipeline, orders, installs, internal handoffs

**Entity types:** quotes, orders, projects, onboarding steps, remediation tickets, procurement→engineering handoff, accepted SOW not scheduled.

**Rules:** stage-age thresholds per tenant template; cross-team **handoff SLA**; **internal ownership** when stage bounces.

---

## 10. Microsoft 365 health, optimisation, upsell

**Themes:** licence vs usage, inactive mailboxes, security baseline gaps, Teams/SharePoint sprawl (later), upsell aligned to **contracted but under-deployed** SKUs, reconciliation to **invoice line items** when finance data exists.

---

## 11. Backup, recovery, managed backup, billing alignment

**Themes:** job success/freshness, protected vs billable workloads, **restore test** evidence, commercial mismatch (sold GB vs used; agent count vs billed), **event** suggestions (recovery workshop).

---

## 12. Billing integrity, revenue assurance, margin protection

**Themes:** billed vs measured counts (seats, mailboxes, agents, storage), **accepted work not invoiced**, **active service not on invoice**, underbilling/overbilling risk, **delivery footprint > contract**, contract renewal mismatch. **Workflow:** finance queue → assign to AM/delivery → link to ticket/opportunity → track resolution. **Future:** Xero/Sage **journal** and **invoice** correlation.

**Knowledge layer:** maintain **persistent** `billing_integrity`-class objects that summarise **variance**, **leakage**, **underbilling**, **remediation path**, and **confidence / gaps**—fed by canonical PSA/accounting data and **refreshed** via `billing_integrity_maintainer` (see §20.7), with lineage—not as a substitute for invoices or ledger truth.

---

## 13. Account manager workspace & next-conversation engine

**Single pane:** priorities for the day per account portfolio; **talk track** (3 bullets + longer optional); **customer-safe wording** for issues; **meeting agenda** and **QBR outline**; **relationship repair** vs **commercial development** modes; **event invite** recommendation with rationale. **Implementation direction:** prefer **reading** maintained account knowledge (`customer_overview`, `relationship_health`, `stalled_work`, `risk_summary`, etc.) and **compose** user-facing prompts on top—reserve live-only synthesis for deltas or missing objects.

---

## 14. Marketing, events, campaign matching

**Flow:** marketing enters **raw event ideas** → AI **refines** for MSP positioning → system **matches accounts** (rules + embeddings later) → **segment summary** → **invite draft** per segment. Support **review campaigns**, **backup/continuity** themes, **AI governance** education events. **Persistent fit signals** (`marketing_fit`, posture objects) should **rank and explain** matches so marketers are not re-running full-account synthesis for every campaign.

---

## 15. Data quality, confidence, blind spots

**Detect missing:** account owner, primary contact, economic buyer, billing/contract link, quote history, M365 telemetry, backup coverage, call history, review history, service plan coverage.

**Present:** **coverage score** per account; **“cannot conclude X because Y is missing”** strings in UI and in AI system prompts as constraints. *Prompts:* `data_gap_summary`, `account_confidence_explanation`, `missing_data_next_steps`. *Direction:* treat **data confidence** as a **maintained knowledge concern**—e.g. `account_confidence` / maintainer output refreshed with sync coverage—not only a single ephemeral score string.

---

## 16. Customer 360 as cross-system workspace (target end-state)

**Tabs / regions (incremental build):** account summary; service summary; risk; recommendations; opportunities & lost quotes; backup/protection; Microsoft posture; finance/billing summary; relationship/stakeholder map; data confidence; QBR/review prep; action history; **unified AI summary** with citations to internal rows and last sync times.

**Principle:** 360 is the **composition layer**—minimal duplicate business logic; each panel reads **canonical APIs** and, over time, **persisted knowledge objects** from the **tenant knowledge layer** (overview, risk narrative, relationship health, billing integrity posture, M365/backup posture, data confidence, QBR-oriented packs)—not only ad hoc LLM calls or raw RAG over synced rows. One-off prompts remain for edge questions; **default narratives** should prefer **refreshed, lineage-bearing** objects where they exist.

---

## 17. Data sources & connector mapping

| Source | Entities ingested (typical) | Product areas enriched | Signals enabled | Cadence | Current vs historical |
|--------|----------------------------|--------------------------|-----------------|---------|------------------------|
| **Autotask** | Accounts, tickets, projects, opps, quotes, contacts | 360, recs, commercial, service risk, stalled work | SLA, stage aging, revenue | Scheduled delta + manual | Current-state primary; events later |
| **ConnectWise** | Same families (mapped) | Same | Same | Same | Same |
| **ITQuoter** | Quotes, lines, versions | Opportunities, marketing, billing | Lost reason, discount, competitor | Periodic + manual | Quote history valuable |
| **Veeam** | Jobs, protected workloads, repositories | Service risk, backup billing | Failed/stale jobs, coverage gaps | Frequent job poll | Current + short history |
| **Microsoft 365 / Entra** | Users, licences, groups, sign-ins (policy-dependent) | M365 health, security, AM | Unused seats, MFA gaps | Periodic | Current-state + trend |
| **Xero / Sage** | Invoices, lines, contacts (later) | Revenue assurance | Billed vs delivered | Daily / webhook | Strong historical |
| **3CX / CDR** | Calls, extensions, queues | Relationship health | Last strategic call | Near-real-time to hourly | Recent window critical |
| **Future RMM** | Devices, patches | Service risk, technical | Device health | Hourly | Current |
| **Future documentation** | Sites, articles | Data quality, QBR | Coverage | Daily | Current |
| **Future CRM** | Campaign responses | Marketing | Engagement | Event-driven | Current + history |

---

## 18. Warehouse & ingestion strategy

**Conceptual stack** (maps to [DATA_INGESTION_AND_WAREHOUSE.md](DATA_INGESTION_AND_WAREHOUSE.md)):

| Tier | Role |
|------|------|
| **A. Raw / synced source** | Payloads from connectors; encrypted config; sync run metadata; `source_entity_mappings`. |
| **B. Canonical operational** | Current-state tenant tables (`customers`, `tickets`, …) — **system of record** for CRM/service/commercial facts. |
| **C. Derived knowledge objects** | **Persistent**, refreshable tenant narratives/summaries/postures (see **Persistent tenant knowledge layer**) — **not** source of truth; **governed** by maintainer prompts and `ai_task_runs`. |
| **D. Scores & recs (today)** | Rule/score engines and `recommendations` — may **feed** knowledge maintainers and 360 until layer C is fully populated. |
| **E. Historical / warehouse / analytics** | Append-only snapshots (future): e.g. daily scores, quote stage events — for reporting without overloading B. |

**Implementation-oriented breakdown:** connection config → `integration_sync_runs` → `source_entity_mappings` → canonical tables → *(future)* knowledge-object store → *(future)* warehouse facts.

**Rules:** **Page-load sync is wrong** for heavy PSA pulls—use **scheduled delta** + **manual sync** for repair and onboarding. **Freshness** requirements vary: ticket backlog **minutes–hours**; financial **daily**; licence counts **daily**; relationship call patterns **hours**. **Reporting** should attach to warehouse facts (tier **E**) without forcing operational tables to carry all history. **Knowledge refreshes** (tier **C**) should run **after** meaningful sync completion or on policy cadence—not on every page view.

---

## 19. AI engine configuration (direction)

- **Per-tenant** provider/model selection and **fallback** chains.  
- **Provider families:** hosted OpenAI-compatible, OpenRouter, self-hosted (**Ollama**, vLLM, LM Studio), **Microsoft / Copilot** path as first-class when adapter exists; others explicit unsupported/stub until dedicated adapter.  
- **Prompt inheritance:** platform defaults → tenant overrides; **versioning** and rollback.  
- **Lineage:** every execution writes **`ai_task_runs`** with provider, model, prompt ids/version ids, and outcome summaries.

---

## 20. Prompt keys for the prompt database

**Rule:** Product-facing templates for the areas below should use these **stable keys** (suffix convention `*.system` or domain-specific as already used in codebase). Do **not** hardcode long system prompts in TS/Python when a prompt row is expected.

### 20.1 Relationship / account management

| Key | Purpose | Likely inputs | Output | Where used |
|-----|---------|----------------|--------|--------------|
| `relationship_health_summary.system` | Summarise relationship strength | Contacts, tickets, meetings, calls | Narrative + drivers | Relationship health page, 360 |
| `account_manager_next_conversation.system` | Next best touch | 360 snapshot, open recs | Bullets + rationale | AM workspace |
| `account_manager_call_script.system` | Talk track | Same | Short script | AM workspace |
| `customer_review_agenda.system` | QBR outline | Commercial + service summary | Agenda sections | Reviews, 360 |
| `stakeholder_gap_explanation.system` | Explain DM/coverage gaps | Contacts, roles | Gap list + suggested actions | 360, relationship |

### 20.2 Risk / recommendations / stalled

| Key | Purpose | Inputs | Output | Where |
|-----|---------|--------|--------|-------|
| `recommendation_explanation.system` | Explain one rec | Rec + customer | Paragraph | Rec queue, 360 |
| `churn_explanation.system` | Churn-style narrative | Risk drivers | Explanation | At-risk, save workspace |
| `risk_summary.system` | Consolidated risk | Tickets, scores | Summary | 360 |
| `stalled_work_explanation.system` | Why stalled | Stage history | Explanation | Stalled work queue |
| `stalled_work_next_action.system` | Next step | Entity type | Action list | Same |

### 20.3 Commercial / marketing

| Key | Purpose | Inputs | Output | Where |
|-----|---------|--------|--------|-------|
| `opportunity_detection.system` | Surface hidden opps | Usage + contracts | Bullets | Commercial, 360 |
| `lost_quote_reactivation.system` | Win-back angle | Lost quote | Outreach draft | Opportunities, marketing |
| `marketing_event_idea_generation.system` | Event themes | Segment, vertical | Idea list | Marketing |
| `campaign_customer_matching.system` | Match accounts to campaign | Idea + account features | Ranked matches | Marketing |
| `campaign_segment_summary.system` | Describe segment | Filter set | Summary | Marketing |
| `event_invite_draft.system` | Invite email | Event + segment | Draft | Marketing |
| `marketing_idea_refinement.system` | Refine marketer text | Raw idea | Polished copy | Marketing |
| `next_best_commercial_conversation.system` | Commercial angle | Pipeline | Talk track | AM workspace |

### 20.4 Billing / finance / leakage

| Key | Purpose | Inputs | Output | Where |
|-----|---------|--------|--------|-------|
| `billing_variance_summary.system` | Explain deltas | Usage vs invoice | Summary table narrative | Revenue assurance |
| `revenue_leakage_explanation.system` | Leakage story | Candidates | Paragraph | Same |
| `billing_remediation_next_action.system` | What to do next | Issue type | Tasks | Same |
| `underbilling_opportunity.system` | Upside cases | Signals | List | Same |

### 20.5 Microsoft / backup / technical

| Key | Purpose | Inputs | Output | Where |
|-----|---------|--------|--------|-------|
| `m365_hygiene_summary.system` | Licence/security hygiene | Graph signals | Summary | M365 health |
| `m365_upsell_opportunity.system` | Upsell | Usage vs entitlements | Bullets | M365 health |
| `backup_risk_summary.system` | Backup posture | Jobs, workloads | Summary | Backup, service risk |
| `backup_gap_opportunity.system` | Sales angle for gaps | Coverage holes | Bullets | Backup, marketing |
| `backup_event_matching.system` | Workshop fit | Backup gaps | Event suggestion | Marketing |
| `technical_gap_summary.system` | Cross-domain gaps | M365+backup+RMM | Narrative | 360, technical |

### 20.6 Data quality / confidence

| Key | Purpose | Inputs | Output | Where |
|-----|---------|--------|--------|-------|
| `data_gap_summary.system` | Missing fields/sources | Coverage model | List | Data quality |
| `account_confidence_explanation.system` | Per-account confidence | Field presence | Explanation | 360 |
| `missing_data_next_steps.system` | How to improve data | Gaps | Steps | Data quality, onboarding |

**Wired in product (tenant):** `customer_review_agenda.system`, `account_manager_next_conversation.system`, and `account_manager_call_script.system` are registered as AI task types with `GET|POST /api/v1/customers/{id}/ai/...` and power the Review/QBR prep and Customer 360 **AI account manager guidance** panel.

**Existing codebase keys** (non-exhaustive): align new keys with patterns in [AI_CONFIGURATION_AND_PROMPTS.md](AI_CONFIGURATION_AND_PROMPTS.md) and seed migrations—extend registry when adding tasks.

### 20.7 Maintainer / knowledge-object refresh keys

These keys are for **scheduled or sync-triggered** runs that **create or refresh persisted knowledge objects** (tenant-scoped, auditable). They are **distinct** from on-demand user keys in §§20.1–20.6: maintainers **write** layer-3 objects; user-facing keys **read** canonical + knowledge + small context windows.

| Maintainer `prompt_key` (planned) | Primary object type | Often pairs with user-facing key |
|-----------------------------------|---------------------|----------------------------------|
| `customer_overview_maintainer.system` | `customer_overview` | `account_summary.system` |
| `relationship_health_maintainer.system` | `relationship_health` | `relationship_health_summary.system` |
| `billing_integrity_maintainer.system` | `billing_integrity` | `billing_variance_summary.system`, `revenue_leakage_explanation.system` |
| `m365_hygiene_maintainer.system` | `m365_hygiene` | `m365_hygiene_summary.system` |
| `backup_posture_maintainer.system` | `backup_posture` | `backup_risk_summary.system` |
| `qbr_prep_maintainer.system` | `qbr_prep` | `customer_review_agenda.system` |
| `data_confidence_maintainer.system` | `account_confidence` (coverage narrative) | `data_gap_summary.system`, `account_confidence_explanation.system` |
| `marketing_fit_maintainer.system` | `marketing_fit` | `campaign_customer_matching.system`, `marketing_event_idea_generation.system` |
| `stalled_work_maintainer.system` | `stalled_work` | `stalled_work_explanation.system`, `stalled_work_next_action.system` |
| `risk_summary_maintainer.system` | `risk_summary` | `risk_summary.system`, `churn_explanation.system` |
| `opportunity_summary_maintainer.system` | `opportunity_summary` | `opportunity_detection.system`, `next_best_commercial_conversation.system` |
| `service_summary_maintainer.system` | `service_summary` | *(future service-facing summary keys)* |

Full conceptual model: **Persistent tenant knowledge layer** (earlier in this doc). Runtime wiring: [AI_CONFIGURATION_AND_PROMPTS.md](AI_CONFIGURATION_AND_PROMPTS.md) § “Knowledge object maintenance”.

---

## 21. Implementation maturity & roadmap sequencing

### 21.1 Suggested sequencing (high level)

1. **Connector expansion** — ConnectWise, deepen Autotask, ITQuoter, Veeam scaffolds to live sync.  
2. **Persistent knowledge layer (foundation)** — Storage model for tenant-scoped knowledge objects; refresh after sync; staleness/lint; maintainer prompt keys (§20.7) registered and executed as `ai_task_runs`; product reads with freshness badges.  
3. **Customer 360 enrichment** — Panels per new data domains; **prefer** maintained knowledge objects for default narratives; single AI “overview” with lineage where live calls remain.  
4. **Billing integrity & revenue assurance** — Rules + finance connector phase 1; **`billing_integrity`** object consumers.  
5. **Microsoft 365 insights** — Read-only hygiene first, then optimisation.  
6. **Backup insights** — Veeam job + billing alignment.  
7. **Telephony** — CDR ingestion for relationship health.  
8. **Campaign / event matching** — Idea bank + match scores + invite drafts; **`marketing_fit`** and posture objects as inputs.  
9. **Richer AM workflows** — Save-the-account state, tasks, playbook library.  
10. **Observability & prompt tooling** — Compare prompt versions, offline eval hooks, safer rollouts.

### 21.2 Intentionally later

Full **workflow automation** ( unattended emails ), **embedding-heavy** personalisation at scale without governance UI, and **multi-tenant data pooling** for ML—out of scope until ethics and legal review.

---

## 22. Appendix — feature matrix (implementation planning)

| section | key value to MSP | main user role | data sources | prompt keys | maturity now | next build phase |
|---------|------------------|----------------|--------------|-------------|--------------|------------------|
| Dashboard | Daily priorities | Director | PSA + canonical | *(future exec summary)* | Existing | Widgets from new domains |
| Customer 360 | One truth | AM, Sales, Service | PSA + future M365/backup | account/risk/churn/rec explain | Partial | Enrich panels |
| Review & QBR prep | Meeting-ready narrative | AM, Director | Customer API + calendar later | customer_review_agenda.system, account_manager_* | Partial (workspace + `?customer_id=`) | AI agenda + notes sync |
| Stalled work | Unlock revenue in pipeline | Ops, Sales | PSA projects/quotes | stalled_work_* | Planned | PSA project sync |
| Relationship health | Prevent silent churn | AM | Tickets, contacts, CDR | relationship_*, stakeholder_* | Planned | Activity model |
| AM workspace | Faster better visits | AM | 360 + recs | account_manager_* | Planned | UI + prompts |
| Save-the-account | Structured retention | AM, Director | Risk + playbook | churn_explanation | Planned | Workflow engine |
| Win-back | Recover lost £ | Sales | Quotes, opps | lost_quote_*, campaign_* | Partial | Execution tracking |
| Revenue assurance | Margin protection | Finance | PSA + accounting | billing_* , revenue_* | Planned | Xero/Sage phase 1 |
| M365 health | Licence & security ROI | Technical | Graph | m365_* | Future | Connector |
| Backup insights | Prove protection | Service | Veeam | backup_* | Future | Connector |
| Telephony | Prove relationship effort | AM | 3CX | relationship_* (augment) | Future | CDR adapter |
| Marketing / events | Fill rooms with right accounts | Marketing | Segments + ideas | marketing_* , event_* | Partial (shell + placeholders) | Idea bank DB + live matching |
| Data quality | Trust & fix gaps | Admin, Ops | Sync + mappings | data_gap_* , account_confidence_* | Wireframed | Coverage APIs |
| **Tenant knowledge layer** | Persisted derived narratives / posture per account | All major surfaces | Canonical + connector coverage | **Maintainer** keys §20.7 + `ai_task_runs` | **Specified** | Schema, refresh jobs, UI freshness |

---

## 23. Additional product ideas (backlog)

- **Prompt A/B and shadow mode** — run alternate prompt versions logged-only for evaluation.  
- **“Explain this score”** everywhere a score appears, with lineage to source rows.  
- **Partner / vendor scorecards** — track subcontractor SLA (future).  
- **Renewal command centre** — contracts + QBR + health in one timeline.  
- **Benchmarking** — anonymised peer percentiles once multi-tenant analytics mature (governance-heavy).  
- **Customer-facing portal (long-term)** — selective transparency; not v1.

---

*Document owner: product + engineering leads. Update this file **before** large implementation slices that introduce new product areas or connectors; keep [ROUTES_UX_MAP.md](ROUTES_UX_MAP.md) and wireframes in sync.*
