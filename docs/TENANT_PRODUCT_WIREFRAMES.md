# Tenant MSP product — wireframes & information architecture

This document defines the **tenant-facing** MSP workspace (the hero product). The **platform console** (`/platform/...`) stays a separate, more operational surface and is not specified here beyond cross-links.

**Master direction:** Full product vision, section matrix, connector map, prompt planning, and roadmap live in **[MSP360_PRODUCT_SPEC.md](MSP360_PRODUCT_SPEC.md)**. Update that file before large new slices; keep this wireframe doc aligned when routes or IA change.

Audience: **MSP owner / service manager** — needs signal, prioritisation, and fast paths to accounts, not raw admin chrome.

---

## Global layout (tenant app shell)

**Purpose:** Persistent frame for all authenticated tenant routes.

**Above the fold:** Workspace name, current user, tenant switcher, primary nav, page title strip.

**Key regions:**

| Region | Content |
|--------|---------|
| **Left sidebar** | Brand, grouped nav (Overview → Operations → Accounts → Workspace → Administration), optional “Help” footer link (future). |
| **Top bar** | Breadcrumb or page title, tenant selector (pill), notifications placeholder (future), user menu (logout / logout all). |
| **Main canvas** | Page content with consistent max-width (~1280px), card rhythm, section headings. |

**Primary actions (global):** Switch tenant, sign out, navigate to Dashboard and Customers.

**Responsive:** Desktop: fixed sidebar. Tablet: collapsible narrow sidebar or icon rail (implemented as scrollable horizontal nav strip on small breakpoints). Mobile: same with stacked top bar.

---

## 1. Dashboard (`/app`)

**Purpose:** Default landing after sign-in — answer “what needs my attention today?” for the MSP.

**Above the fold (MSP owner/manager):**

1. **Executive KPI row** — total accounts, high-risk count, open recommendations, lost quotes to revisit (`GET /api/v1/dashboards/executive`). **Each KPI is a link** into the relevant workspace (`/app/customers`, `/app/at-risk`, `/app/recommendations`, `/app/opportunities?tab=lost`).
2. **Two priority columns** — “At-risk accounts” and “Needs attention” (short lists from customer API with `status` filters + **Open workspace** → `/app/at-risk` and `/app/attention`).
3. **Backup & service risk row** — summary copy + **Open overview** → `/app/service-risk` (`GET /api/v1/workspace/service-risk`).

**Key widgets/cards:**

- KPI tiles (4): Customers, High risk, Open recommendations, Lost quotes revisit.
- List card: At-risk customers (name, scores snippet, CTA “Open account”).
- List card: Attention / watch list.
- Placeholder card: Backup & service risk — “Connect backup/RMM sources to populate” (empty state).

**Primary actions:** Click-through KPIs, **Open workspace** on each panel, row links to customer 360, onboarding link when incomplete (`/app/onboarding`).

**Tables/lists:** Short lists (max ~8 rows each); not full data grids.

**Later / below the fold:** Recent activity feed, team tasks, integration health strip.

---

## 2. Customers / Accounts (`/app/customers`)

**Purpose:** Searchable directory of managed accounts with health and next action visible.

**Above the fold:** Page title, search, status filter, first rows of the table (or empty state).

**Key widgets:**

- Search + status filter bar.
- **Data table** (product-style: zebra/hover, sticky header on scroll, status badges).
- Pagination.

**Columns (priority):** Name (link), Status badge, Owner, Health scores (compact visual), Next best action (truncated with tooltip future).

**Primary actions:** Open account (row click / link), filter by at-risk / watch.

**Later:** Saved views, bulk assign owner, export CSV.

---

## 3. Customer 360 / Account detail (`/app/customers/:id`)

**Purpose:** Single-account intelligence workspace — scores, recommendations, support & revenue context.

**Above the fold:** Breadcrumb back to list, account name + status + owner, **score strip** (risk / attention / growth as prominent cards).

**Key sections (vertical order):**

1. **Score overview** — three metric cards with short interpretation text.
2. **Operational snapshot** — open tickets, opportunities, quotes (existing counts).
3. **Segmented areas** — **Overview** (scores + operational snapshot counts), **Recommendations** (typed rows + link to tenant queue), **Pipeline** (opportunities + quotes tables), **Activity** (recent actions).
4. Deep link **`#workspace`** selects the Recommendations tab for drill-through from queues.

**Primary actions:** Back to customers, open full recommendation queue filtered to account, open commercial hub.

**Later:** Embedded charts, notes, support trends tab.

**Direction (knowledge layer):** as the **persistent tenant knowledge base** ships (see [MSP360_PRODUCT_SPEC.md](MSP360_PRODUCT_SPEC.md)), default **overview / risk / relationship / billing / posture / confidence** copy should **read maintained knowledge objects** (with freshness and lineage) and reserve **live AI** for gaps, user questions, or stale-object fallback—not only raw RAG over synced rows.

---

## 4. Recommendations queue (`/app/recommendations`)

**Purpose:** Cross-account operational queue — what the MSP should do next.

**API:** `GET /api/v1/workspace/recommendations` (filters: `status`, `scope`, `customer_id`, `owner`, pagination). `PATCH /api/v1/workspace/recommendations/{id}` with `{ "status" }` for **tenant_admin** (`membership:write`).

**Above the fold:** Filter toolbar + first rows of the table (account, category, priority, summary, next action, owner, status, age).

**Primary actions:** Open customer 360, accept / reject / complete (admins), link to full queue from account pages.

---

## 5. Opportunities & quotes hub (`/app/opportunities`)

**Purpose:** Commercial follow-up — pipeline, active quotes, and lost-quote revisits.

**API:** `GET /api/v1/workspace/commercial` returns `opportunities`, `lost_quotes`, `open_quotes`.

**Above the fold:** Segmented control (New opportunities | Open & draft quotes | Lost — revisit) + table per segment.

**Primary actions:** Drill to account / 360, align with dashboard lost-quote KPI (`?tab=lost`).

---

## 6. At-risk accounts (`/app/at-risk`)

**Purpose:** Working list of `status=at_risk` customers with risk score, owner, and next-best-action text.

**API:** `GET /api/v1/customers?status=at_risk` (existing customers list).

**Primary actions:** Open customer 360, use dashboard KPI + panel links.

---

## 7. Needs-attention accounts (`/app/attention`)

**Purpose:** Watch-list accounts (`status=watch`) needing proactive attention.

**API:** `GET /api/v1/customers?status=watch`.

**Primary actions:** Same as at-risk hub; dashboard “Needs attention” panel links here.

---

## 8. Backup & service risk (`/app/service-risk`)

**Purpose:** Product area for backup coverage/jobs and service-delivery pressure.

**API:** `GET /api/v1/workspace/service-risk` — backup section is a **placeholder** with copy; delivery section includes live **open ticket** and **at-risk account** counts.

**Primary actions:** Links onward to at-risk / needs-attention workspaces; grows as integrations connect.

---

## 9. Members (`/app/members`)

**Purpose:** Team and invitations for the tenant.

**Above the fold:** Member count, invite CTA, member table.

**Key tables:** Members, pending invitations.

**Primary actions:** Invite user, revoke invite, change role (per permissions).

**Later:** SSO group mapping, activity per member.

---

## 10. Security (`/app/security`)

**Purpose:** Sessions and sign-out controls.

**Above the fold:** Session list, revoke others, logout all.

**Later:** SSO enforcement, device posture.

---

## 11. Integrations (`/app/integrations`)

**Purpose:** Connected systems (PSA, RMM, M365, etc.).

**Above the fold:** Connection cards with status.

**Later:** OAuth connect flows, sync logs.

---

## 12. Onboarding (`/app/onboarding`)

**Purpose:** First-run checklist for new MSP workspace.

**Above the fold:** Progress stepper, primary checklist items.

**Primary actions:** Mark steps complete, link to customers/integrations.

---

## 13. Review & QBR prep (`/app/reviews`)

**Purpose:** Account-review preparation workspace for QBRs, service reviews, and commercial check-ins — not a calendar replacement.

**Above the fold:** Account selector (or `?customer_id=` deep link from Customer 360), “what to cover” summary, KPI strip when an account is loaded.

**Key regions:** health KPIs; what to cover; risks & open recommendations; commercial snapshot; relationship/stakeholder placeholder; data confidence / blind spots; **AI account manager guidance** preview shell (prompt-registry keys documented, no live model call); local review agenda textarea (placeholder); suggested next steps.

**APIs today:** `GET /api/v1/customers`, `GET /api/v1/customers/{id}` for live context. Future: calendar, notes sync, `customer_review_agenda.system` output.

**Primary actions:** Choose account → open Customer 360; jump to recommendations / commercial hub / data quality.

---

## 14. Marketing, events & campaigns (`/app/marketing`)

**Purpose:** MSP marketing and account-development planning — segments, event themes, and customer→campaign matching direction.

**Above the fold:** Campaign-ready segment cards (mix of live links and preview copy), event idea board with theme chips, matching panel with illustrative scores.

**Key regions:** segment placeholders (lost quotes, nurture, review invites, service-pain→commercial); event idea board (themes: AI intro, backup, M365, cyber, etc.); customer→event matching preview; marketing notes textarea; **AI account manager guidance** compact shell for commercial motions.

**Future:** persisted idea bank, AI generation (`marketing_event_idea_generation.system`), matching (`campaign_customer_matching.system`), invite drafts (`event_invite_draft.system`).

---

## Navigation IA (implemented vs planned)

| Area | Route (current) | Status |
|------|-----------------|--------|
| Dashboard | `/app` | **Implemented** |
| Recommendations | `/app/recommendations` | **Implemented** |
| Opportunities & quotes | `/app/opportunities` | **Implemented** |
| At-risk workspace | `/app/at-risk` | **Implemented** |
| Needs attention | `/app/attention` | **Implemented** |
| Service risk | `/app/service-risk` | **Implemented** (backup placeholder + live delivery counts) |
| Marketing, events & campaigns | `/app/marketing` | **Partial** — product shell: segments, event board, matching previews, AM guidance placeholder |
| Review & QBR prep | `/app/reviews` (+ optional `?customer_id=`) | **Partial** — live account context when selected; AI agenda later |
| Data quality | `/app/data-quality` | **Implemented** (shell / sync view) |
| Customers | `/app/customers` | **Implemented** |
| Customer 360 | `/app/customers/:id` | **Implemented** |
| Members | `/app/members` | **Implemented** |
| Security | `/app/security` | **Implemented** |
| Integrations | `/app/integrations` | **Implemented** |
| Onboarding | `/app/onboarding` | **Implemented** |
| System status | `/app/system-status` | **Implemented** |
| Product roadmap (placeholder hub + topics) | `/app/roadmap`, `/app/roadmap/:topic` | **Placeholder** — IA visibility only until connectors/APIs land |

---

## Visual / UX principles (tenant)

- **Hero product:** Light canvas, generous whitespace, **Plus Jakarta Sans** (display) + neutral body stack.
- **Accent:** Teal / cyan family for primary actions (distinct from platform’s dark + sky-blue operator theme).
- **Cards** over naked tables where narrative matters; tables remain for dense directories with strong header design.
- **Empty states:** Illustration placeholder + one sentence + primary CTA.
- **Version:** Shown subtly on auth pages and app shell footer.

See also: [ROUTES_UX_MAP.md](ROUTES_UX_MAP.md) for route ↔ layout mapping.
