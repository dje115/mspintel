import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { ExecutiveDashboardResponse, IntegrationCoverageResponse, RiskQueueRow } from "../../api/types";
import { useSession } from "../../state/session";

export function DashboardPage() {
  const { accessToken, currentTenantId } = useSession();
  const [exec, setExec] = useState<ExecutiveDashboardResponse | null>(null);
  const [atRisk, setAtRisk] = useState<RiskQueueRow[]>([]);
  const [watch, setWatch] = useState<RiskQueueRow[]>([]);
  const [coverage, setCoverage] = useState<IntegrationCoverageResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadError(null);
    void Promise.all([
      api.executiveDashboard(accessToken, currentTenantId),
      api.riskQueue(accessToken, currentTenantId, { mode: "at_risk", page: 1, page_size: 8 }),
      api.riskQueue(accessToken, currentTenantId, { mode: "attention", page: 1, page_size: 8 })
    ])
      .then(([e, ar, w]) => {
        setExec(e);
        setAtRisk(ar.items);
        setWatch(w.items);
      })
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Unable to load dashboard");
      });
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api
      .integrationCoverage(accessToken, currentTenantId)
      .then(setCoverage)
      .catch(() => setCoverage(null));
  }, [accessToken, currentTenantId]);

  if (loadError) {
    return (
      <div>
        <div className="tenant-page-head">
          <h1 className="tenant-page-title">Dashboard</h1>
          <p className="tenant-error">{loadError}</p>
        </div>
      </div>
    );
  }

  if (!exec) {
    return <div className="tenant-skeleton">Loading your workspace…</div>;
  }

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Dashboard</h1>
        <p className="tenant-page-sub">
          Front door to your operating queues: jump into recommendations, commercial follow-ups, account risk, and
          service delivery signals. Each tile below is clickable.
        </p>
      </header>

      <section className="tenant-kpi-row" aria-label="Executive summary">
        <Link className="tenant-kpi tenant-kpi--link" to="/app/customers">
          <p className="tenant-kpi-label">Accounts</p>
          <p className="tenant-kpi-value">{exec.customers}</p>
          <p className="tenant-kpi-hint">Open directory →</p>
        </Link>
        <Link className="tenant-kpi tenant-kpi--link" to="/app/at-risk">
          <p className="tenant-kpi-label">High risk</p>
          <p className="tenant-kpi-value">{exec.high_risk_customers}</p>
          <p className="tenant-kpi-hint">At-risk workspace →</p>
        </Link>
        <Link className="tenant-kpi tenant-kpi--link" to="/app/recommendations">
          <p className="tenant-kpi-label">Open recommendations</p>
          <p className="tenant-kpi-value">{exec.open_recommendations}</p>
          <p className="tenant-kpi-hint">Action queue →</p>
        </Link>
        <Link className="tenant-kpi tenant-kpi--link" to="/app/opportunities?tab=lost">
          <p className="tenant-kpi-label">Lost quotes</p>
          <p className="tenant-kpi-value">{exec.lost_quotes_revisit_count}</p>
          <p className="tenant-kpi-hint">Commercial hub →</p>
        </Link>
      </section>

      {coverage ? (
        <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Integration &amp; mapping health</h2>
            <Link className="tenant-panel-link" to="/app/data-quality">
              Full data quality →
            </Link>
          </div>
          <div className="tenant-panel-body tenant-op-grid" style={{ padding: "1rem 1.1rem" }}>
            <div>
              <div className="tenant-kpi-label">Connected sources</div>
              <div className="tenant-kpi-value tenant-kpi-value--inline">{coverage.connected_systems}</div>
            </div>
            <div>
              <div className="tenant-kpi-label">Unresolved mappings</div>
              <div className="tenant-kpi-value tenant-kpi-value--inline">{coverage.unresolved_mappings}</div>
            </div>
            <div>
              <div className="tenant-kpi-label">Weak mapping signals</div>
              <div className="tenant-kpi-value tenant-kpi-value--inline">{coverage.weak_mappings}</div>
            </div>
          </div>
          <div className="tenant-panel-body" style={{ paddingTop: 0 }}>
            <p className="muted" style={{ margin: 0, fontSize: "0.88rem" }}>
              Clear mapping backlog to keep customer names, finance, and service views trustworthy.
            </p>
            <p style={{ marginTop: "0.75rem", marginBottom: 0 }}>
              <Link className="tenant-btn-inline tenant-btn-inline--ghost" to="/app/integrations/mappings">
                Open mapping review
              </Link>
            </p>
          </div>
        </section>
      ) : null}

      <div className="tenant-two-col">
        <section className="tenant-panel tenant-panel--accent">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Review &amp; QBR prep</h2>
            <Link className="tenant-panel-link" to="/app/reviews">
              Open workspace →
            </Link>
          </div>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
            <p className="muted" style={{ marginTop: 0 }}>
              Pick an account to assemble health, commercial, relationship, and data-confidence context before customer
              reviews. Use <strong>Review prep</strong> from Customer 360 to continue with the same account selected.
            </p>
            <Link className="tenant-btn-inline" to="/app/reviews">
              Start review prep
            </Link>
          </div>
        </section>
        <section className="tenant-panel tenant-panel--accent">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Marketing &amp; events</h2>
            <Link className="tenant-panel-link" to="/app/marketing">
              Open workspace →
            </Link>
          </div>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
            <p className="muted" style={{ marginTop: 0 }}>
              Commercial segments and event planning — lost-quote counts and customer links already reflect synced data;
              AI-assisted matching arrives as prompts and rules expand.
            </p>
            <Link className="tenant-btn-inline" to="/app/marketing">
              Plan campaigns
            </Link>
          </div>
        </section>
      </div>

      <div className="tenant-two-col">
        <section className="tenant-panel">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">At-risk accounts</h2>
            <Link className="tenant-panel-link" to="/app/at-risk">
              Open workspace →
            </Link>
          </div>
          <div className="tenant-panel-body">
            {atRisk.length === 0 ? (
              <div className="tenant-empty">
                <p className="tenant-empty-title">No at-risk accounts in this slice</p>
                <p>When scores cross thresholds, they will surface here automatically.</p>
              </div>
            ) : (
              <div className="tenant-table-wrap">
                <table className="tenant-table">
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Risk</th>
                      <th>Next action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {atRisk.map((c) => (
                      <tr key={c.customer_id}>
                        <td>
                          <Link to={`/app/customers/${c.customer_id}`}>{c.customer_name}</Link>
                        </td>
                        <td>{c.risk_score}</td>
                        <td className="muted" style={{ maxWidth: "14rem" }}>
                          {c.top_reasons[0] ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        <section className="tenant-panel">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Needs attention</h2>
            <Link className="tenant-panel-link" to="/app/attention">
              Open workspace →
            </Link>
          </div>
          <div className="tenant-panel-body">
            {watch.length === 0 ? (
              <div className="tenant-empty">
                <p className="tenant-empty-title">No watch-list accounts</p>
                <p>Use customer health rules to flag accounts for proactive outreach.</p>
              </div>
            ) : (
              <div className="tenant-table-wrap">
                <table className="tenant-table">
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Attention</th>
                      <th>Next action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {watch.map((c) => (
                      <tr key={c.customer_id}>
                        <td>
                          <Link to={`/app/customers/${c.customer_id}`}>{c.customer_name}</Link>
                        </td>
                        <td>{c.attention_score}</td>
                        <td className="muted" style={{ maxWidth: "14rem" }}>
                          {c.top_reasons[0] ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Backup &amp; service risk</h2>
          <Link className="tenant-panel-link" to="/app/service-risk">
            Open overview →
          </Link>
        </div>
        <div className="tenant-panel-body">
          <div className="tenant-empty" style={{ textAlign: "left", maxWidth: "40rem", margin: "0 auto" }}>
            <p className="tenant-empty-title">Structured risk workspace</p>
            <p>
              Service delivery metrics are live from tickets and scores; backup panels reflect registered backup
              integrations and future job sync.
            </p>
          </div>
        </div>
      </section>

      <section className="tenant-grid tenant-grid--cards-3" style={{ marginTop: "1rem" }}>
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>Account development</h3>
          <p className="tenant-page-sub">Pair watch-list accounts with review prep and commercial follow-up.</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            <Link className="tenant-btn-inline tenant-btn-inline--ghost" to="/app/attention">
              Needs attention
            </Link>
            <Link className="tenant-btn-inline" to="/app/reviews">
              Review prep
            </Link>
          </div>
        </article>
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>Integration operations</h3>
          <p className="tenant-page-sub">Manage Autotask connector health, test credentials, and trigger syncs.</p>
          <Link className="tenant-btn-inline" to="/app/integrations">
            Open integrations
          </Link>
        </article>
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>Data quality</h3>
          <p className="tenant-page-sub">Review sync freshness and connector coverage for downstream product trust.</p>
          <Link className="tenant-btn-inline" to="/app/data-quality">
            Open data quality
          </Link>
        </article>
      </section>
    </div>
  );
}
