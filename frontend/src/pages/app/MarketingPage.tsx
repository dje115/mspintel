import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import type { ExecutiveDashboardResponse } from "../../api/types";
import { AccountManagerGuidanceShell } from "../../components/AccountManagerGuidanceShell";
import { TenantAiContextNotice } from "../../components/TenantAiContextNotice";
import { useSession } from "../../state/session";

const EVENT_THEMES = [
  { id: "ai_intro", label: "AI introduction", hint: "Governance + quick wins" },
  { id: "backup", label: "Backup strategy", hint: "Coverage & recovery story" },
  { id: "recovery_test", label: "Recovery testing", hint: "Tabletop / restore evidence" },
  { id: "m365", label: "Microsoft 365 optimisation", hint: "Licences + adoption" },
  { id: "cyber", label: "Cyber / security awareness", hint: "Human layer + controls" },
  { id: "compliance", label: "Compliance / governance", hint: "Audit-ready narrative" },
  { id: "continuity", label: "Continuity / disaster recovery", hint: "RTO/RPO clarity" },
  { id: "cost", label: "Cost optimisation", hint: "Right-size stack" },
  { id: "modern_work", label: "Modern workplace / productivity", hint: "Teams, SharePoint, collab" }
] as const;

const PLANNING_STARTERS = [
  {
    title: "Backup confidence breakfast",
    theme: "Backup strategy",
    note: "Best once backup job health is synced — use Service risk and integrations for coverage first."
  },
  {
    title: "M365 cost & security clinic",
    theme: "Microsoft 365 optimisation",
    note: "Pairs with M365 Health and licence signals from your connected Microsoft source."
  },
  {
    title: "AI in the MSP stack (no hype)",
    theme: "AI introduction",
    note: "Grounded session on governance — aligns with how your tenant uses AI engines and prompts."
  }
];

export function MarketingPage() {
  const [searchParams] = useSearchParams();
  const focusCustomerId = searchParams.get("customer_id") ?? "";
  const { accessToken, currentTenantId } = useSession();
  const [dash, setDash] = useState<ExecutiveDashboardResponse | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api
      .executiveDashboard(accessToken, currentTenantId)
      .then(setDash)
      .catch(() => setDash(null));
  }, [accessToken, currentTenantId]);

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Marketing, events &amp; campaigns</h1>
        <p className="tenant-page-sub">
          Plan commercial follow-up, nurture, and event-led growth. Segment ranking and AI-generated copy will grow as
          more connectors stay in sync — for now, use the links below to work from live pipeline and risk queues.
          {focusCustomerId ? (
            <>
              {" "}
              <strong>Account context is on</strong> — AM guidance below follows the customer you opened from Customer
              360 or Review prep.
            </>
          ) : null}
        </p>
      </header>
      <TenantAiContextNotice compact />

      <section className="tenant-panel tenant-panel--accent">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Campaign-ready segments</h2>
          <span className="tenant-badge tenant-badge--muted">Rules + AI (expanding)</span>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
          <p className="muted" style={{ marginTop: 0 }}>
            These tiles jump to real workspaces. Lists use your synced customers, quotes, tickets, and scores where
            those sources are connected.
          </p>
          <div className="tenant-grid tenant-grid--cards-3">
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Lost quotes — follow up</h3>
              <p className="tenant-page-sub muted">
                {dash != null ? (
                  <>
                    <strong>{dash.lost_quotes_revisit_count}</strong> lost quote
                    {dash.lost_quotes_revisit_count === 1 ? "" : "s"} flagged for revisit in the commercial hub.
                  </>
                ) : (
                  "Open the commercial hub to see lost quotes from your PSA or quoting connector."
                )}
              </p>
              <Link to="/app/opportunities?tab=lost" className="tenant-btn-inline">
                Open lost quotes
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Nurture — growth headroom</h3>
              <p className="tenant-page-sub muted">
                Healthy accounts with thin pipeline — segment rules will appear here as coverage improves.
              </p>
              <Link to="/app/customers" className="tenant-btn-inline tenant-btn-inline--ghost">
                Browse customers
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Review / QBR invite list</h3>
              <p className="tenant-page-sub muted">
                Cadence and calendar hints are planned; use review prep to prioritise accounts today.
              </p>
              <Link to="/app/reviews" className="tenant-btn-inline tenant-btn-inline--ghost">
                Open review prep
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Account-development candidates</h3>
              <p className="tenant-page-sub muted">Watch-list and medium-attention accounts for proactive outreach.</p>
              <Link to="/app/attention" className="tenant-btn-inline tenant-btn-inline--ghost">
                Needs attention
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Service pain → commercial</h3>
              <p className="tenant-page-sub muted">
                Ticket load and repeat incidents will feed campaign ideas when service data is synced.
              </p>
              <Link to="/app/service-risk" className="tenant-btn-inline tenant-btn-inline--ghost">
                Service risk
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>At-risk — save motion</h3>
              <p className="tenant-page-sub muted">Pair outreach with accounts that need a deliberate save plan.</p>
              <Link to="/app/at-risk" className="tenant-btn-inline tenant-btn-inline--ghost">
                At-risk workspace
              </Link>
            </article>
          </div>
        </div>
      </section>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Event idea board</h2>
          <span className="tenant-badge tenant-badge--muted">Planning starters</span>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Starters below are not generated from live accounts — they are workshop prompts. Event ideas from signals
            and invite drafts will use your tenant&apos;s prompt library under <strong>Prompts</strong> once those tasks
            are enabled.
          </p>
          <div className="tenant-event-theme-grid" style={{ marginBottom: "1rem" }}>
            {EVENT_THEMES.map((t) => (
              <span key={t.id} className="tenant-event-chip" title={t.hint}>
                {t.label}
              </span>
            ))}
          </div>
          <div className="tenant-grid tenant-grid--cards-3">
            {PLANNING_STARTERS.map((idea) => (
              <article key={idea.title} className="tenant-card">
                <p className="tenant-badge tenant-badge--muted" style={{ marginBottom: "0.35rem" }}>
                  {idea.theme}
                </p>
                <h3 style={{ marginTop: 0 }}>{idea.title}</h3>
                <p className="tenant-page-sub muted">{idea.note}</p>
                <p className="muted" style={{ fontSize: "0.78rem", marginBottom: 0 }}>
                  Status, owner, and linked segments will be added in a later release.
                </p>
              </article>
            ))}
          </div>
          <label className="tenant-marketing-notes-label" htmlFor="marketing-idea-notes">
            Workshop notes
          </label>
          <textarea
            id="marketing-idea-notes"
            className="tenant-review-notes"
            rows={4}
            placeholder="Capture ideas for your next campaign workshop — saved drafts will arrive in a later release."
          />
        </div>
      </section>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Customer → event matching</h2>
          <span className="tenant-badge tenant-badge--muted">Not live yet</span>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Ranked matches and invite drafts need segment rules plus optional AI — we are not showing sample scores or
            fake accounts, because that would look like real product output.
          </p>
          <div className="tenant-empty" style={{ textAlign: "left", maxWidth: "40rem" }}>
            <p className="tenant-empty-title">Matching will appear here</p>
            <p className="muted" style={{ marginBottom: 0 }}>
              When shipped, each row will show a customer, a suggested event theme, a plain-English reason, and
              confidence — all tied to synced data and prompt versions you control.
            </p>
          </div>
        </div>
      </section>

      <AccountManagerGuidanceShell
        customerId={focusCustomerId || undefined}
        contextLine={
          focusCustomerId
            ? "Marketing workspace · account-scoped next conversation + call script"
            : "Open a customer from Customer 360 or Review prep to generate talk tracks here."
        }
        compact
      />
    </div>
  );
}
