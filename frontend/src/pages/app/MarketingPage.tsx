import { Link, useSearchParams } from "react-router-dom";

import { AccountManagerGuidanceShell } from "../../components/AccountManagerGuidanceShell";
import { TenantAiContextNotice } from "../../components/TenantAiContextNotice";

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

const SAMPLE_EVENT_IDEAS = [
  { title: "Backup confidence breakfast", theme: "Backup strategy", note: "Invite accounts with stale job signals once Veeam sync lands." },
  { title: "M365 cost & security clinic", theme: "Microsoft 365 optimisation", note: "Pairs with licence reconciliation from Graph (planned)." },
  { title: "AI in the MSP stack (no hype)", theme: "AI introduction", note: "Grounded session on prompt governance — ties to tenant AI settings." }
];

export function MarketingPage() {
  const [searchParams] = useSearchParams();
  const focusCustomerId = searchParams.get("customer_id") ?? "";

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Marketing, events &amp; campaigns</h1>
        <p className="tenant-page-sub">
          Plan commercial follow-up, nurture, and event-led growth in one workspace. Segments and matching below are
          product shells — ranking and copy will later come from connector-backed data and prompt-driven AI.
          {focusCustomerId ? (
            <>
              {" "}
              <strong>Account context loaded</strong> — AM guidance below uses{" "}
              <code className="tenant-code-inline">?customer_id=</code> for talk tracks (add this query from Customer
              360 or review prep).
            </>
          ) : null}
        </p>
      </header>
      <TenantAiContextNotice compact />

      <section className="tenant-panel tenant-panel--accent">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Campaign-ready segments (preview)</h2>
          <span className="tenant-badge tenant-badge--muted">Future: rules + AI</span>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Placeholder segments show the intended UX. Real lists will use PSA + backup + M365 signals. Summaries will use{" "}
            <code className="tenant-code-inline">campaign_segment_summary.system</code>.
          </p>
          <div className="tenant-grid tenant-grid--cards-3">
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Lost quote — high value</h3>
              <p className="tenant-page-sub muted">Accounts with recent lost quotes above a value threshold.</p>
              <Link to="/app/opportunities?tab=lost" className="tenant-btn-inline">
                Open lost quotes
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Nurture — growth headroom</h3>
              <p className="tenant-page-sub muted">Healthy scores, low expansion pipeline (heuristic TBD).</p>
              <span className="muted" style={{ fontSize: "0.82rem" }}>
                Prompt: <code className="tenant-code-inline">next_best_commercial_conversation.system</code>
              </span>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Review / QBR invite list</h3>
              <p className="tenant-page-sub muted">Strategic reviews due or overdue (calendar integration later).</p>
              <Link to="/app/reviews" className="tenant-btn-inline tenant-btn-inline--ghost">
                Open review prep
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Account-development candidates</h3>
              <p className="tenant-page-sub muted">Watch-list and medium-growth accounts for proactive outreach.</p>
              <Link to="/app/attention" className="tenant-btn-inline tenant-btn-inline--ghost">
                Needs attention
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Service pain → commercial</h3>
              <p className="tenant-page-sub muted">
                Accounts where ticket load or repeat incidents imply upsell (rules engine later).
              </p>
              <span className="muted" style={{ fontSize: "0.82rem" }}>
                Signals: PSA tickets + service-risk API (growing).
              </span>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>At-risk — save motion</h3>
              <p className="tenant-page-sub muted">Pair campaigns with save plans once retention workspace ships.</p>
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
          <span className="tenant-badge tenant-badge--muted">Manual + AI later</span>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Marketing will add ideas here; AI will suggest additions from account signals using{" "}
            <code className="tenant-code-inline">marketing_event_idea_generation.system</code> and refine copy with{" "}
            <code className="tenant-code-inline">marketing_idea_refinement.system</code>.
          </p>
          <div className="tenant-event-theme-grid" style={{ marginBottom: "1rem" }}>
            {EVENT_THEMES.map((t) => (
              <span key={t.id} className="tenant-event-chip" title={t.hint}>
                {t.label}
              </span>
            ))}
          </div>
          <div className="tenant-grid tenant-grid--cards-3">
            {SAMPLE_EVENT_IDEAS.map((idea) => (
              <article key={idea.title} className="tenant-card">
                <p className="tenant-badge tenant-badge--muted" style={{ marginBottom: "0.35rem" }}>
                  {idea.theme}
                </p>
                <h3 style={{ marginTop: 0 }}>{idea.title}</h3>
                <p className="tenant-page-sub muted">{idea.note}</p>
                <p className="muted" style={{ fontSize: "0.78rem", marginBottom: 0 }}>
                  Future: status (draft / scheduled), owner, linked segment.
                </p>
              </article>
            ))}
          </div>
          <label className="tenant-marketing-notes-label" htmlFor="marketing-idea-notes">
            Marketing notes (placeholder)
          </label>
          <textarea
            id="marketing-idea-notes"
            className="tenant-review-notes"
            rows={4}
            placeholder="Capture raw ideas for the next campaign workshop — autosave and collaboration in a later release."
          />
        </div>
      </section>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Customer → event / campaign matching</h2>
          <span className="tenant-badge tenant-badge--muted">Coming soon</span>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Matching will combine segment rules, optional embeddings, and explainable reasons. Primary prompt family:{" "}
            <code className="tenant-code-inline">campaign_customer_matching.system</code> with invite drafts from{" "}
            <code className="tenant-code-inline">event_invite_draft.system</code>.
          </p>
          <div className="tenant-grid tenant-grid--cards-3">
            <article className="tenant-card tenant-card--match-placeholder">
              <h3 style={{ marginTop: 0 }}>Match score (example)</h3>
              <p className="tenant-match-score" aria-hidden="true">
                0.82
              </p>
              <p className="tenant-page-sub muted">Northwind Health → “Backup confidence breakfast” (illustrative only).</p>
              <p className="muted" style={{ fontSize: "0.78rem" }}>
                Improves with: backup job freshness, risk score, stakeholder count.
              </p>
            </article>
            <article className="tenant-card tenant-card--match-placeholder">
              <h3 style={{ marginTop: 0 }}>Match score (example)</h3>
              <p className="tenant-match-score" aria-hidden="true">
                0.74
              </p>
              <p className="tenant-page-sub muted">Contoso Logistics → “M365 cost &amp; security clinic”.</p>
              <p className="muted" style={{ fontSize: "0.78rem" }}>
                Improves with: Graph licence deltas, help-desk volume.
              </p>
            </article>
            <article className="tenant-card tenant-card--match-placeholder">
              <h3 style={{ marginTop: 0 }}>Match score (example)</h3>
              <p className="tenant-match-score" aria-hidden="true">
                0.61
              </p>
              <p className="tenant-page-sub muted">Fabrikam Retail → “AI in the MSP stack (no hype)”.</p>
              <p className="muted" style={{ fontSize: "0.78rem" }}>
                Improves with: AI usage flags, leadership persona detection (future).
              </p>
            </article>
          </div>
        </div>
      </section>

      <AccountManagerGuidanceShell
        customerId={focusCustomerId || undefined}
        contextLine={
          focusCustomerId
            ? "Marketing workspace · account-scoped next conversation + call script"
            : "Commercial and marketing motions — add ?customer_id= to generate talk tracks here."
        }
        compact
      />
    </div>
  );
}
