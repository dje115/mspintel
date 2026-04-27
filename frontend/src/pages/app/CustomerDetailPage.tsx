import { useEffect, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import { AccountManagerGuidanceShell } from "../../components/AccountManagerGuidanceShell";
import { CustomerAiInsights } from "../../components/CustomerAiInsights";
import type { CustomerDetailResponse, OpportunityRow, QuoteRow, RecommendationRow } from "../../api/types";
import { ScoreMeter } from "../../components/ScoreMeter";
import { useSession } from "../../state/session";
import { formatAge, formatShortDate, formatUsdFromCents } from "../../utils/formatWorkspace";

type DetailTab = "overview" | "queue" | "commercial" | "activity";

function RecommendationCards({
  rows,
  summaryFallback,
  customerId
}: {
  rows: RecommendationRow[];
  summaryFallback: string[];
  customerId: string;
}) {
  if (rows.length === 0 && summaryFallback.length === 0) {
    return (
      <div className="tenant-empty">
        <p className="tenant-empty-title">No open recommendations</p>
        <p>When the engine proposes actions, they appear here and in the tenant-wide queue.</p>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <ul className="tenant-list-plain">
        {summaryFallback.map((s) => (
          <li key={s} className="tenant-rec-card">
            {s}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="tenant-queue-cards">
      {rows.map((r) => (
        <article key={r.id} className="tenant-queue-card">
          <div className="tenant-queue-card-head">
            <span className={`tenant-badge ${r.priority === "high" ? "tenant-badge--at_risk" : "tenant-badge--muted"}`}>
              {r.priority}
            </span>
            <span className="tenant-badge tenant-badge--muted">{r.status}</span>
            <span className="tenant-badge tenant-badge--watch">{r.scope}</span>
          </div>
          <p className="tenant-queue-card-title">{r.summary}</p>
          <p className="muted tenant-queue-card-meta">{r.suggested_next_action}</p>
          <p className="muted tenant-queue-card-meta" style={{ fontSize: "0.8rem" }}>
            {formatAge(r.created_at)} ago · Owner {r.owner_name ?? "—"}
          </p>
          <div className="tenant-queue-card-actions">
            <Link className="tenant-btn-inline" to={`/app/recommendations?customer_id=${customerId}`}>
              Full queue
            </Link>
          </div>
        </article>
      ))}
    </div>
  );
}

function MiniTableOpps({ rows }: { rows: OpportunityRow[] }) {
  if (rows.length === 0) {
    return <p className="muted">No opportunities on file for this account.</p>;
  }
  return (
    <div className="tenant-table-wrap">
      <table className="tenant-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Value</th>
            <th>Opened</th>
            <th>Next</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.id}>
              <td>{o.title}</td>
              <td>{o.status}</td>
              <td>{formatUsdFromCents(o.value_cents)}</td>
              <td>{formatShortDate(o.created_at)}</td>
              <td className="muted">{o.suggested_next_action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MiniTableQuotes({ rows }: { rows: QuoteRow[] }) {
  if (rows.length === 0) {
    return <p className="muted">No quotes on file for this account.</p>;
  }
  return (
    <div className="tenant-table-wrap">
      <table className="tenant-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Value</th>
            <th>Date</th>
            <th>Signal</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((q) => (
            <tr key={q.id}>
              <td>{q.title}</td>
              <td>{q.status}</td>
              <td>{formatUsdFromCents(q.value_cents)}</td>
              <td>{formatShortDate(q.created_at)}</td>
              <td className="muted">{q.revisit_reason ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CustomerDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { accessToken, currentTenantId } = useSession();
  const aiHighlight = searchParams.get("ai") === "risk" ? "risk" : null;
  const [data, setData] = useState<CustomerDetailResponse | null>(null);
  const [tab, setTab] = useState<DetailTab>("overview");

  useEffect(() => {
    if (location.hash === "#workspace") setTab("queue");
  }, [location.hash]);

  useEffect(() => {
    if (!accessToken || !currentTenantId || !id) return;
    void api.customerDetail(accessToken, currentTenantId, id).then(setData);
  }, [accessToken, currentTenantId, id]);

  if (!data) {
    return <div className="tenant-skeleton">Loading account intelligence…</div>;
  }

  const scores = data.latest_scores;
  const recommendations = data.recommendations ?? [];
  const opportunities = data.opportunities ?? [];
  const quotes = data.quotes ?? [];

  return (
    <div>
      <nav className="tenant-breadcrumb" aria-label="Breadcrumb">
        <Link to="/app/customers">Accounts</Link>
        <span> / </span>
        <span>{data.name}</span>
      </nav>

      <header className="tenant-page-head">
        <h1 className="tenant-hero-title">{data.name}</h1>
        <p className="tenant-hero-meta">
          <span
            className={`tenant-badge ${
              data.status === "at_risk"
                ? "tenant-badge--at_risk"
                : data.status === "watch"
                  ? "tenant-badge--watch"
                  : data.status === "active"
                    ? "tenant-badge--active"
                    : "tenant-badge--muted"
            }`}
            style={{ marginRight: "0.5rem" }}
          >
            {data.status.split("_").join(" ")}
          </span>
          Owner: <strong style={{ color: "#334155" }}>{data.owner_name ?? "Unassigned"}</strong>
        </p>
        <div className="tenant-hero-actions">
          <Link className="tenant-btn-inline" to={`/app/reviews?customer_id=${data.id}`}>
            Prepare review / QBR
          </Link>
          <Link className="tenant-btn-inline tenant-btn-inline--ghost" to={`/app/marketing?customer_id=${data.id}`}>
            Marketing &amp; events
          </Link>
        </div>
      </header>

      <div className="tenant-segmented tenant-segmented--detail" role="tablist" aria-label="Account sections">
        {(
          [
            ["overview", "Overview"],
            ["queue", "Recommendations"],
            ["commercial", "Pipeline"],
            ["activity", "Activity"]
          ] as const
        ).map(([k, label]) => (
          <button key={k} type="button" className={`tenant-segment${tab === k ? " is-active" : ""}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <>
          <section className="tenant-metric-grid" aria-label="Health scores">
            <article className="tenant-metric-card">
              <h3>Risk</h3>
              <p className="tenant-metric-big">{scores?.risk_score ?? "—"}</p>
              <ScoreMeter label="Signal" value={scores?.risk_score} variant="risk" />
              <p className="tenant-metric-note">Churn, SLA, and support load proxies. Higher = more risk.</p>
            </article>
            <article className="tenant-metric-card">
              <h3>Attention</h3>
              <p className="tenant-metric-big">{scores?.attention_score ?? "—"}</p>
              <ScoreMeter label="Signal" value={scores?.attention_score} />
              <p className="tenant-metric-note">Tasks, ageing tickets, and unanswered client signals.</p>
            </article>
            <article className="tenant-metric-card">
              <h3>Growth</h3>
              <p className="tenant-metric-big">{scores?.growth_score ?? "—"}</p>
              <ScoreMeter label="Signal" value={scores?.growth_score} />
              <p className="tenant-metric-note">Expansion, adoption, and revenue momentum indicators.</p>
            </article>
          </section>

          {data.risk_engine ? (
            <section className="tenant-panel" style={{ marginTop: "1rem" }}>
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Risk Engine v1 summary</h2>
                <span className="tenant-badge tenant-badge--watch">
                  {data.risk_engine.scoring_version} · {data.risk_engine.confidence_level} confidence
                </span>
              </div>
              <div className="tenant-panel-body tenant-op-grid">
                <div>
                  <div className="tenant-kpi-label">Risk level</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">{data.risk_engine.risk_level}</div>
                </div>
                <div>
                  <div className="tenant-kpi-label">Attention level</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">{data.risk_engine.attention_level}</div>
                </div>
                <div>
                  <div className="tenant-kpi-label">Calculated</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">{data.risk_engine.calculated_at ?? "—"}</div>
                </div>
              </div>
              <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
                <p className="tenant-kpi-label">Primary factors</p>
                {data.risk_engine.factors.length === 0 ? (
                  <p className="muted" style={{ marginTop: 0 }}>
                    No high-impact factors captured in this snapshot.
                  </p>
                ) : (
                  <ul className="tenant-list-plain">
                    {data.risk_engine.factors.slice(0, 5).map((f, idx) => (
                      <li key={`${idx}-${String(f.code ?? "factor")}`} className="tenant-rec-card">
                        <strong>{String(f.title ?? f.code ?? "factor")}</strong>
                        {f.evidence ? <span className="muted"> — {String(f.evidence)}</span> : null}
                      </li>
                    ))}
                  </ul>
                )}
                {data.risk_engine.coverage_notes.length > 0 ? (
                  <>
                    <p className="tenant-kpi-label">Confidence / blind spots</p>
                    <ul className="tenant-list-plain">
                      {data.risk_engine.coverage_notes.map((n) => (
                        <li key={n} className="tenant-rec-card muted">
                          {n}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : null}
              </div>
            </section>
          ) : null}

          {data.finance ? (
            <section className="tenant-panel" style={{ marginTop: "1rem" }}>
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Finance &amp; billing alignment</h2>
                <span className={`tenant-badge ${data.finance.finance_linked ? "tenant-badge--active" : "tenant-badge--muted"}`}>
                  {data.finance.finance_linked ? "Canonical finance linked" : "No canonical finance link"}
                </span>
              </div>
              <div className="tenant-panel-body tenant-op-grid">
                <div>
                  <div className="tenant-kpi-label">Snapshot</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">{data.finance.snapshot_effective_date ?? "—"}</div>
                  <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.35rem" }}>
                    {data.finance.display_name ?? "Billing account"}
                    {data.finance.currency_code ? ` · ${data.finance.currency_code}` : ""}
                  </p>
                </div>
                <div>
                  <div className="tenant-kpi-label">Mailboxes billed / service</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">
                    {data.finance.billed_mailboxes ?? "—"} / {data.finance.service_active_mailboxes ?? "—"}
                  </div>
                  <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.35rem" }}>
                    Users billed / licensed: {data.finance.billed_users ?? "—"} / {data.finance.service_licensed_users ?? "—"}
                  </p>
                </div>
                <div>
                  <div className="tenant-kpi-label">Confidence</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">{data.finance.confidence_level ?? "—"}</div>
                  <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.35rem" }}>
                    Payment friction: {data.finance.payment_status_summary ?? "—"}
                    {data.finance.aged_outstanding_cents != null && data.finance.aged_outstanding_cents > 0
                      ? ` · Aged outstanding ${formatUsdFromCents(data.finance.aged_outstanding_cents)}`
                      : ""}
                  </p>
                </div>
              </div>
              {data.finance.integrity_highlights.length > 0 ? (
                <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
                  <p className="tenant-kpi-label">Integrity highlights</p>
                  <ul className="tenant-list-plain">
                    {data.finance.integrity_highlights.map((h) => (
                      <li key={h} className="tenant-rec-card">
                        {h}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {data.finance.confidence_notes.length > 0 ? (
                <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
                  <p className="tenant-kpi-label">Blind spots &amp; notes</p>
                  <ul className="tenant-list-plain">
                    {data.finance.confidence_notes.map((n) => (
                      <li key={n} className="tenant-rec-card muted">
                        {n}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
                <p className="muted" style={{ fontSize: "0.85rem", margin: 0 }}>
                  <strong>Next commercial move:</strong> {data.finance.next_commercial_action_placeholder}
                </p>
                <p style={{ marginTop: "0.75rem" }}>
                  <Link className="tenant-btn-inline tenant-btn-inline--ghost" to="/app/billing-integrity">
                    Open billing integrity workspace
                  </Link>
                </p>
              </div>
            </section>
          ) : null}

          {data.m365 ? (
            <section className="tenant-panel" style={{ marginTop: "1rem" }}>
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Microsoft 365 posture</h2>
                <span className={`tenant-badge ${data.m365.linked ? "tenant-badge--active" : "tenant-badge--muted"}`}>
                  {data.m365.linked ? "M365 posture linked" : "No M365 posture sync"}
                </span>
              </div>
              <div className="tenant-panel-body tenant-op-grid">
                <div>
                  <div className="tenant-kpi-label">Licensed / active / inactive</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">
                    {data.m365.licensed_users ?? "—"} / {data.m365.active_users_30d ?? "—"} / {data.m365.inactive_users_30d ?? "—"}
                  </div>
                </div>
                <div>
                  <div className="tenant-kpi-label">Mailboxes</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">
                    {data.m365.mailbox_count ?? "—"} (shared {data.m365.shared_mailbox_count ?? "—"})
                  </div>
                </div>
                <div>
                  <div className="tenant-kpi-label">MFA / confidence</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">
                    {data.m365.mfa_coverage_pct ?? "—"}% · {data.m365.confidence_level}
                  </div>
                  <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.35rem" }}>
                    Unused licences: {data.m365.unused_licences ?? "—"}
                  </p>
                </div>
              </div>
              {[...data.m365.hygiene_findings, ...data.m365.optimisation_findings].length > 0 ? (
                <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
                  <p className="tenant-kpi-label">Hygiene & optimisation highlights</p>
                  <ul className="tenant-list-plain">
                    {[...data.m365.hygiene_findings, ...data.m365.optimisation_findings].map((h) => (
                      <li key={h} className="tenant-rec-card">
                        {h}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {data.m365.confidence_notes.length > 0 ? (
                <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
                  <p className="tenant-kpi-label">Coverage notes</p>
                  <ul className="tenant-list-plain">
                    {data.m365.confidence_notes.map((n) => (
                      <li key={n} className="tenant-rec-card muted">
                        {n}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
                <p className="muted" style={{ fontSize: "0.85rem", margin: 0 }}>
                  <strong>Next technical/commercial step:</strong> {data.m365.next_action_placeholder}
                </p>
                <p style={{ marginTop: "0.75rem" }}>
                  <Link className="tenant-btn-inline tenant-btn-inline--ghost" to="/app/m365-health">
                    Open M365 health workspace
                  </Link>
                </p>
              </div>
            </section>
          ) : null}

          {data.connector_coverage ? (
            <section className="tenant-panel" style={{ marginTop: "1rem" }}>
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Connector coverage confidence</h2>
              </div>
              <div className="tenant-panel-body tenant-op-grid">
                <div>
                  <div className="tenant-kpi-label">Contributing systems</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">
                    {data.connector_coverage.connected_systems.join(", ") || "none"}
                  </div>
                </div>
                <div>
                  <div className="tenant-kpi-label">Missing linked systems</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">
                    {data.connector_coverage.missing_systems.join(", ") || "none"}
                  </div>
                </div>
                <div>
                  <div className="tenant-kpi-label">Unresolved mappings</div>
                  <div className="tenant-kpi-value tenant-kpi-value--inline">
                    {data.connector_coverage.unresolved_mapping_count}
                  </div>
                </div>
              </div>
              <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
                <p className="muted" style={{ margin: 0 }}>{data.connector_coverage.confidence_note}</p>
              </div>
            </section>
          ) : null}

          {data.demo_profile && (data.demo_profile as { synthetic?: boolean }).synthetic ? (
            <section className="tenant-panel" style={{ marginTop: "1rem" }}>
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Demo dataset context (synthetic)</h2>
              </div>
              <div className="tenant-panel-body">
                <p className="muted" style={{ marginTop: 0 }}>
                  Fictional UK-style scenario bundled with the <code>demo-msp</code> seed for product and AI testing — not
                  live connector output.
                </p>
                <pre
                  className="muted"
                  style={{
                    fontSize: "0.75rem",
                    maxHeight: "14rem",
                    overflow: "auto",
                    marginTop: "0.75rem",
                    padding: "0.75rem",
                    background: "#0f172a08",
                    borderRadius: 6
                  }}
                >
                  {JSON.stringify(data.demo_profile, null, 2)}
                </pre>
              </div>
            </section>
          ) : null}

          <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Operational snapshot</h2>
              <Link className="tenant-panel-link" to="/app/opportunities">
                Commercial hub
              </Link>
            </div>
            <div className="tenant-panel-body tenant-op-grid">
              <div>
                <div className="tenant-kpi-label">Open tickets</div>
                <div className="tenant-kpi-value tenant-kpi-value--inline">{data.open_tickets_count}</div>
                <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.35rem" }}>
                  Delivery pressure from PSA sync.
                </p>
              </div>
              <div>
                <div className="tenant-kpi-label">Open opportunities</div>
                <div className="tenant-kpi-value tenant-kpi-value--inline">{data.open_opportunities_count}</div>
                <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.35rem" }}>
                  Pipeline items linked to this account.
                </p>
              </div>
              <div>
                <div className="tenant-kpi-label">Open / lost quotes</div>
                <div className="tenant-kpi-value tenant-kpi-value--inline">{data.open_quotes_count}</div>
                <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.35rem" }}>
                  Includes lost rows worth revisiting.
                </p>
              </div>
            </div>
          </section>

          <CustomerAiInsights customerId={data.id} highlight={aiHighlight} />

          <AccountManagerGuidanceShell customerId={data.id} contextLine={`Customer 360 · ${data.name}`} />
        </>
      ) : null}

      {tab === "queue" ? (
        <section className="tenant-panel" id="workspace">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Recommendations</h2>
            <Link className="tenant-panel-link" to={`/app/recommendations?customer_id=${data.id}`}>
              Open in queue
            </Link>
          </div>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
            <RecommendationCards
              rows={recommendations}
              summaryFallback={data.recommendation_summary}
              customerId={data.id}
            />
          </div>
        </section>
      ) : null}

      {tab === "commercial" ? (
        <div className="tenant-stack-panels">
          <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Opportunities</h2>
              <Link className="tenant-panel-link" to="/app/opportunities">
                Hub
              </Link>
            </div>
            <div className="tenant-panel-body">
              <MiniTableOpps rows={opportunities} />
            </div>
          </section>
          <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Quotes</h2>
            </div>
            <div className="tenant-panel-body">
              <MiniTableQuotes rows={quotes} />
            </div>
          </section>
        </div>
      ) : null}

      {tab === "activity" ? (
        <section className="tenant-panel" id="account-actions">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Recent activity</h2>
          </div>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
            {data.recent_actions.length === 0 ? (
              <div className="tenant-empty">
                <p className="tenant-empty-title">No recent events</p>
                <p>Timeline will aggregate tickets, quotes, and playbook steps as connectors deepen.</p>
              </div>
            ) : (
              <ul className="tenant-list-plain">
                {data.recent_actions.map((a) => (
                  <li key={a} className="tenant-rec-card">
                    {a}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
