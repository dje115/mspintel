# Tenant MSP product — wireframes & information architecture

This document defines the **tenant-facing** MSP workspace (the hero product). The **platform console** (`/platform/...`) stays a separate, more operational surface and is not specified here beyond cross-links.

Audience: **MSP owner / service manager** — needs signal, prioritisation, and fast paths to accounts, not raw admin chrome.

---

## Global layout (tenant app shell)

**Purpose:** Persistent frame for all authenticated tenant routes.

**Above the fold:** Workspace name, current user, tenant switcher, primary nav, page title strip.

**Key regions:**

| Region | Content |
|--------|---------|
| **Left sidebar** | Brand, grouped nav (Overview → Intelligence → Workspace → Administration), optional “Help” footer link (future). |
| **Top bar** | Breadcrumb or page title, tenant selector (pill), notifications placeholder (future), user menu (logout / logout all). |
| **Main canvas** | Page content with consistent max-width (~1280px), card rhythm, section headings. |

**Primary actions (global):** Switch tenant, sign out, navigate to Dashboard and Customers.

**Responsive:** Desktop: fixed sidebar. Tablet: collapsible narrow sidebar or icon rail (implemented as scrollable horizontal nav strip on small breakpoints). Mobile: same with stacked top bar.

---

## 1. Dashboard (`/app`)

**Purpose:** Default landing after sign-in — answer “what needs my attention today?” for the MSP.

**Above the fold (MSP owner/manager):**

1. **Executive KPI row** — total accounts, high-risk count, open recommendations, lost quotes to revisit (wired to `GET /api/v1/dashboards/executive` today).
2. **Two priority columns** — “At-risk accounts” and “Needs attention” (short lists from customer API with `status` filters + deep links).
3. **Single row placeholder** — “Backup & service risk” summary card (placeholder until integration-backed metrics exist).

**Key widgets/cards:**

- KPI tiles (4): Customers, High risk, Open recommendations, Lost quotes revisit.
- List card: At-risk customers (name, scores snippet, CTA “Open account”).
- List card: Attention / watch list.
- Placeholder card: Backup & service risk — “Connect backup/RMM sources to populate” (empty state).

**Primary actions:** “View all customers”, open a specific account, “Complete onboarding” if step incomplete (link to `/app/onboarding`).

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
3. **Recommendations** — card list (not plain `<ul>`); each item actionable placeholder.
4. **Recent activity** — timeline-style list (compact).
5. **Future tabs (documented only):** Support trends | Opportunities & quotes | Backup/RMM risk — can ship as single scroll page first.

**Primary actions:** Back to customers, future: “Add note”, “Create opportunity”.

**Later:** Tabbed layout, embedded charts, document vault.

---

## 4. Recommendations / Next best actions (future route: e.g. `/app/recommendations`)

**Purpose:** Cross-account queue of open executive recommendations.

**Above the fold:** Count of open items, sorted queue, filters by severity/owner.

**Key widgets:** Filter bar, table of recommendation rows (account, summary, age, status).

**Primary actions:** Open account, mark done (when API exists).

**Today:** Surfaced on **Dashboard** and **Customer 360**; full queue page deferred.

---

## 5. Opportunities / Lost quotes (future: `/app/opportunities`)

**Purpose:** Pipeline and lost-quote reactivation.

**Above the fold:** Pipeline KPIs, list of lost quotes with “revisit” flag.

**Today:** `lost_quotes_revisit_count` on dashboard; detail placeholders on account page later.

---

## 6. At-risk customers (view mode on `/app/customers?status=at_risk` or future `/app/at-risk`)

**Purpose:** Fast slice of worst health accounts.

**Above the fold:** Pre-filtered list, explainer strip (“Accounts scoring above risk threshold”).

**Today:** Filter on customers list + dashboard column.

---

## 7. Attention-needed customers (same pattern, `status=watch`)

**Purpose:** Accounts needing follow-up without full “at risk” severity.

**Today:** Dashboard column + customer filter.

---

## 8. Backup / service risk (future: `/app/service-risk` or tab on dashboard)

**Purpose:** RMM/backup integration signals, SLA breach risk.

**Today:** Dashboard placeholder card + copy in wireframe; no new backend.

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

## Navigation IA (implemented vs planned)

| Area | Route (current) | Status |
|------|-----------------|--------|
| Dashboard | `/app` | **Implemented** |
| Customers | `/app/customers` | **Implemented** |
| Customer 360 | `/app/customers/:id` | **Implemented** |
| Members | `/app/members` | **Implemented** |
| Security | `/app/security` | **Implemented** |
| Integrations | `/app/integrations` | **Implemented** |
| Onboarding | `/app/onboarding` | **Implemented** |
| System status | `/app/system-status` | **Implemented** |
| Recommendations queue | — | Planned |
| Opportunities / lost quotes | — | Planned (partial metrics on dashboard) |
| At-risk / attention hubs | — | Use list filters + dashboard |
| Backup / service risk | — | Planned |

---

## Visual / UX principles (tenant)

- **Hero product:** Light canvas, generous whitespace, **Plus Jakarta Sans** (display) + neutral body stack.
- **Accent:** Teal / cyan family for primary actions (distinct from platform’s dark + sky-blue operator theme).
- **Cards** over naked tables where narrative matters; tables remain for dense directories with strong header design.
- **Empty states:** Illustration placeholder + one sentence + primary CTA.
- **Version:** Shown subtly on auth pages and app shell footer.

See also: [ROUTES_UX_MAP.md](ROUTES_UX_MAP.md) for route ↔ layout mapping.
