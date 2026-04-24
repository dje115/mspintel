import { Link, useParams } from "react-router-dom";

const ROADMAP_TOPICS: { slug: string; title: string; summary: string }[] = [
  {
    slug: "tenant-knowledge-layer",
    title: "Tenant knowledge layer (AI-maintained)",
    summary:
      "Persistent, refreshable knowledge objects between canonical sync data and product surfaces—lineage, staleness, and maintainer prompts; specified in the master product spec and data/AI docs."
  },
  {
    slug: "billing-integrity",
    title: "Revenue assurance & billing integrity",
    summary:
      "Billed vs actual usage, uninvoiced work, contract vs delivery footprint, and finance correlation—specified for implementation in the master product spec."
  },
  {
    slug: "m365-health",
    title: "Microsoft 365 health & licence optimisation",
    summary:
      "Hygiene, stale accounts, licence mismatch, security posture over time, and upsell aligned to usage—depends on a future Microsoft/Graph-class connector."
  },
  {
    slug: "relationship-health",
    title: "Relationship health & stakeholder coverage",
    summary:
      "Low contact, support-only relationships, missing decision-makers, and QBR cadence—driven by contacts, activities, and eventually telephony."
  },
  {
    slug: "stalled-work",
    title: "Stalled work & handoffs",
    summary:
      "Stalled quotes, installs, projects, onboarding, and internal sales→service→projects handoffs—queue UX specified; PSA entity depth TBD per connector."
  },
  {
    slug: "account-manager-workspace",
    title: "Account manager workspace",
    summary:
      "Next conversation, talk track, meeting agendas, and customer-safe explanations—tight integration with Customer 360 and prompt keys in the spec."
  },
  {
    slug: "event-ideas",
    title: "Event ideas & campaign themes",
    summary:
      "Marketing-captured ideas, AI refinement, and event matching to accounts—extends the Marketing & growth area."
  },
  {
    slug: "campaign-matching",
    title: "Campaign matching & segments",
    summary:
      "Match accounts to campaigns and produce segment summaries and invite drafts—prompt-driven per master spec §21."
  },
  {
    slug: "telephony-insights",
    title: "Telephony & call insights",
    summary:
      "3CX/CDR-style ingestion for relationship truth and AM cadence—future connector; see data-source mapping in the spec."
  },
  {
    slug: "finance-intelligence",
    title: "Finance intelligence",
    summary:
      "Cross-cut of commercial PSA data with accounting (Xero/Sage) for margin and leakage narratives—later phase."
  }
];

export function RoadmapHubPage() {
  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Product roadmap</h1>
        <p className="tenant-page-sub">
          Planned customer-intelligence areas from the master product specification. These pages are intentionally lightweight until
          the underlying connectors and APIs ship.
        </p>
      </header>

      <section className="tenant-grid tenant-grid--cards-3">
        {ROADMAP_TOPICS.map((t) => (
          <article key={t.slug} className="tenant-card">
            <h3 style={{ marginTop: 0 }}>{t.title}</h3>
            <p className="tenant-page-sub">{t.summary}</p>
            <Link to={`/app/roadmap/${t.slug}`} className="tenant-btn-inline">
              View placeholder
            </Link>
          </article>
        ))}
      </section>

      <p className="muted" style={{ marginTop: "1.5rem" }}>
        Source of truth: <code>docs/MSP360_PRODUCT_SPEC.md</code> in the repository.
      </p>
    </div>
  );
}

export function RoadmapTopicPage() {
  const { topic } = useParams<{ topic: string }>();
  const meta = ROADMAP_TOPICS.find((t) => t.slug === topic);

  if (!meta) {
    return (
      <div>
        <header className="tenant-page-head">
          <h1 className="tenant-page-title">Unknown roadmap topic</h1>
          <p className="tenant-page-sub">This slug is not in the roadmap index.</p>
          <Link to="/app/roadmap" className="tenant-btn-inline">
            Back to roadmap
          </Link>
        </header>
      </div>
    );
  }

  return (
    <div>
      <header className="tenant-page-head">
        <p className="tenant-page-sub" style={{ marginBottom: "0.5rem" }}>
          <Link to="/app/roadmap">← Product roadmap</Link>
        </p>
        <h1 className="tenant-page-title">{meta.title}</h1>
        <p className="tenant-page-sub">{meta.summary}</p>
      </header>

      <section className="tenant-card" style={{ maxWidth: 720 }}>
        <p>
          This screen reserves navigation and routing for <strong>{meta.title}</strong>. Behaviour, APIs, and AI task types will be
          implemented in a later phase per <code>docs/MSP360_PRODUCT_SPEC.md</code>.
        </p>
        <p className="muted">No backend mutations occur from this placeholder.</p>
      </section>
    </div>
  );
}
