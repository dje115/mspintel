import { Link } from "react-router-dom";

export function MarketingPage() {
  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Marketing & growth</h1>
        <p className="tenant-page-sub">
          MSP-specific campaign planning surface for lost quote reactivation, nurture sequences, and account development.
        </p>
      </header>

      <section className="tenant-grid tenant-grid--cards-3">
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>Lost quote reactivation</h3>
          <p className="tenant-page-sub">Prioritize recently lost deals with re-open signals and owner follow-up prompts.</p>
          <p className="muted">Next: one-click campaign drafts and win-back task bundles.</p>
          <Link to="/app/opportunities?tab=lost" className="tenant-btn-inline">
            Open lost quotes
          </Link>
        </article>
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>Nurture candidates</h3>
          <p className="tenant-page-sub">Accounts with growth headroom and low recent touch frequency.</p>
          <p className="muted">Next: cadence templates, email/call playbooks, and response tracking.</p>
        </article>
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>QBR & review invite list</h3>
          <p className="tenant-page-sub">High-value customers due for strategic reviews and roadmap planning.</p>
          <Link to="/app/reviews" className="tenant-btn-inline tenant-btn-inline--ghost">
            Open review prep
          </Link>
        </article>
      </section>
    </div>
  );
}
