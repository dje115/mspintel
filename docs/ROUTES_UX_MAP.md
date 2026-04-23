# Routes and UX map (mspintel SPA)

Single React SPA (`frontend/`). Layout is chosen by **route prefix**, not by user type alone (tenant vs platform are different trees).

---

## Layout components

| Layout | File | Visual identity |
|--------|------|-------------------|
| **PublicLayout** | `layout/PublicLayout.tsx` | Centered **tenant** auth canvas: soft gradient, **tenant-auth-card**, marketing-friendly. Used for `/login`, `/signup`, `/accept-invitation`. |
| **AppLayout** | `layout/AppLayout.tsx` | **Tenant product shell**: light sidebar + top bar, **Plus Jakarta Sans** headings, teal accent — main MSP workspace. |
| **PlatformLayout** | `layout/PlatformLayout.tsx` | **Platform console**: dark sidebar, operational tone, distinct from tenant (do not merge styling). |
| **None (full page)** | — | `/platform/login` uses its own full-page **platform** dark gradient (`PlatformLoginPage`). |

---

## Public tenant auth routes

| Path | Page | Layout | Notes |
|------|------|--------|-------|
| `/login` | `LoginPage` | PublicLayout | MSP workspace sign-in; link to platform console. |
| `/signup` | `SignupPage` | PublicLayout | Creates tenant + owner; redirects to onboarding. |
| `/accept-invitation` | `AcceptInvitationPage` | PublicLayout | Query `?token=`; same visual family as login. |

---

## Tenant product routes (`TenantProtectedRoute` + `AppLayout`)

All require tenant JWT and tenant context (`X-Tenant-Id` from session).

| Path | Page | Notes |
|------|------|-------|
| `/app` | `DashboardPage` | Default post-login landing; executive KPIs (click-through) + priority lists + workspace links. |
| `/app/recommendations` | `RecommendationsPage` | Cross-account recommendation queue. |
| `/app/opportunities` | `OpportunitiesPage` | Commercial hub; optional `?tab=opportunities`, `pipeline`, or `lost`. |
| `/app/at-risk` | `AtRiskAccountsPage` | At-risk account operating list. |
| `/app/attention` | `NeedsAttentionAccountsPage` | Needs-attention (watch) operating list. |
| `/app/service-risk` | `ServiceRiskPage` | Backup + service delivery risk overview. |
| `/app/customers` | `CustomersPage` | Account directory. |
| `/app/customers/:id` | `CustomerDetailPage` | Customer 360; `#workspace` opens the recommendations tab. |
| `/app/onboarding` | `OnboardingPage` | Workspace checklist. |
| `/app/integrations` | `IntegrationsPage` | Connections list. |
| `/app/members` | `MembersPage` | Team + invitations. |
| `/app/security` | `SecurityPage` | Sessions. |
| `/app/system-status` | `SystemStatusPage` | Tenant-scoped API status (admin capability). |

**Redirect:** `/` → `/login`.

**Legacy default:** Previously `/app` redirected to `/app/customers`; now **`/app` is the dashboard**.

---

## Platform console routes

| Path | Page | Layout / guard |
|------|------|----------------|
| `/platform/login` | `PlatformLoginPage` | No layout; standalone operator login (+ MFA). |
| `/platform` | `PlatformOverviewPage` | `PlatformProtectedRoute` → `PlatformLayout` |
| `/platform/tenants` | `PlatformTenantsPage` | same |
| `/platform/system-status` | `PlatformSystemStatusPage` | same |
| `/platform/security` | `PlatformSecurityPage` | same |

---

## Route guards

| Component | Behaviour |
|-----------|-----------|
| `TenantProtectedRoute` | Requires access token; loads `/auth/me`; ensures tenant membership; wraps **AppLayout** children. |
| `PlatformProtectedRoute` | Requires platform-scoped session; wraps **PlatformLayout** children. |
| `FallbackNavigate` | Unknown paths → sensible default (`/login` or `/app` if token present). |

---

## Cross-links (UX)

- Tenant **login** footer → “Platform console sign-in” → `/platform/login`.
- Platform login may reference tenant app URL for confusion avoidance (optional copy).

---

## Deep links

- `/app/recommendations?customer_id=<uuid>` — queue filtered to one account.
- `/app/opportunities?tab=lost` — lost-quote revisit list.
- `/app/customers/<uuid>#workspace` — customer 360 with recommendations tab.

See [TENANT_PRODUCT_WIREFRAMES.md](TENANT_PRODUCT_WIREFRAMES.md) for IA detail; routes are registered in `App.tsx` under **AppLayout**.
