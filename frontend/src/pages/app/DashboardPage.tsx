import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { CustomerListItem, ExecutiveDashboardResponse } from "../../api/types";
import { useSession } from "../../state/session";

export function DashboardPage() {
  const { accessToken, currentTenantId } = useSession();
  const [exec, setExec] = useState<ExecutiveDashboardResponse | null>(null);
  const [atRisk, setAtRisk] = useState<CustomerListItem[]>([]);
  const [watch, setWatch] = useState<CustomerListItem[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadError(null);
    void Promise.all([
      api.executiveDashboard(accessToken, currentTenantId),
      api.customers(accessToken, currentTenantId, { page: 1, page_size: 8, status: "at_risk" }),
      api.customers(accessToken, currentTenantId, { page: 1, page_size: 8, status: "watch" })
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
          Prioritised view of account health, recommendations, and revenue follow-ups for your MSP. Deeper queues
          for opportunities and service risk will appear here as integrations mature.
        </p>
      </header>

      <section className="tenant-kpi-row" aria-label="Executive summary">
        <article className="tenant-kpi">
          <p className="tenant-kpi-label">Accounts</p>
          <p className="tenant-kpi-value">{exec.customers}</p>
          <p className="tenant-kpi-hint">Managed customers</p>
        </article>
        <article className="tenant-kpi">
          <p className="tenant-kpi-label">High risk</p>
          <p className="tenant-kpi-value">{exec.high_risk_customers}</p>
          <p className="tenant-kpi-hint">Needs leadership attention</p>
        </article>
        <article className="tenant-kpi">
          <p className="tenant-kpi-label">Open recommendations</p>
          <p className="tenant-kpi-value">{exec.open_recommendations}</p>
          <p className="tenant-kpi-hint">Executive scope</p>
        </article>
        <article className="tenant-kpi">
          <p className="tenant-kpi-label">Lost quotes</p>
          <p className="tenant-kpi-value">{exec.lost_quotes_revisit_count}</p>
          <p className="tenant-kpi-hint">Worth revisiting</p>
        </article>
      </section>

      <div className="tenant-two-col">
        <section className="tenant-panel">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">At-risk accounts</h2>
            <Link className="tenant-panel-link" to="/app/customers?status=at_risk">
              View all
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
                      <tr key={c.id}>
                        <td>
                          <Link to={`/app/customers/${c.id}`}>{c.name}</Link>
                        </td>
                        <td>{c.risk_score ?? "—"}</td>
                        <td className="muted" style={{ maxWidth: "14rem" }}>
                          {c.next_best_action ?? "—"}
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
            <Link className="tenant-panel-link" to="/app/customers?status=watch">
              View all
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
                      <tr key={c.id}>
                        <td>
                          <Link to={`/app/customers/${c.id}`}>{c.name}</Link>
                        </td>
                        <td>{c.attention_score ?? "—"}</td>
                        <td className="muted" style={{ maxWidth: "14rem" }}>
                          {c.next_best_action ?? "—"}
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
        </div>
        <div className="tenant-panel-body">
          <div className="tenant-empty">
            <p className="tenant-empty-title">Connect backup &amp; RMM signals</p>
            <p>
              This panel will summarise backup coverage gaps, failed jobs, and SLA risk per account. See the
              product wireframes in the repository (<code style={{ fontSize: "0.85rem" }}>docs/TENANT_PRODUCT_WIREFRAMES.md</code>).
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
