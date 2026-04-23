import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import type { CustomerDetailResponse } from "../../api/types";
import { ScoreMeter } from "../../components/ScoreMeter";
import { useSession } from "../../state/session";

export function CustomerDetailPage() {
  const { id } = useParams();
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<CustomerDetailResponse | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId || !id) return;
    void api.customerDetail(accessToken, currentTenantId, id).then(setData);
  }, [accessToken, currentTenantId, id]);

  if (!data) {
    return <div className="tenant-skeleton">Loading account intelligence…</div>;
  }

  const scores = data.latest_scores;

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
      </header>

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

      <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Operational snapshot</h2>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
          <div>
            <div className="tenant-kpi-label">Open tickets</div>
            <div className="tenant-kpi-value" style={{ fontSize: "1.35rem" }}>
              {data.open_tickets_count}
            </div>
          </div>
          <div>
            <div className="tenant-kpi-label">Open opportunities</div>
            <div className="tenant-kpi-value" style={{ fontSize: "1.35rem" }}>
              {data.open_opportunities_count}
            </div>
          </div>
          <div>
            <div className="tenant-kpi-label">Open / lost quotes</div>
            <div className="tenant-kpi-value" style={{ fontSize: "1.35rem" }}>
              {data.open_quotes_count}
            </div>
          </div>
        </div>
      </section>

      <div className="tenant-two-col">
        <section className="tenant-panel">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Recommendations</h2>
          </div>
          <div className="tenant-panel-body">
            {data.recommendation_summary.length === 0 ? (
              <div className="tenant-empty">
                <p className="tenant-empty-title">No open recommendations</p>
                <p>When the engine proposes actions, they will appear as actionable cards here.</p>
              </div>
            ) : (
              data.recommendation_summary.map((r) => (
                <div key={r} className="tenant-rec-card">
                  {r}
                </div>
              ))
            )}
          </div>
        </section>

        <section className="tenant-panel">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Recent activity</h2>
          </div>
          <div className="tenant-panel-body">
            {data.recent_actions.length === 0 ? (
              <div className="tenant-empty">
                <p className="tenant-empty-title">No recent events</p>
                <p>Timeline will aggregate tickets, quotes, and playbook steps.</p>
              </div>
            ) : (
              <ul className="tenant-list-plain">
                {data.recent_actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Account workspace</h2>
        </div>
        <div className="tenant-panel-body">
          <div className="tenant-empty" style={{ textAlign: "left", maxWidth: "40rem" }}>
            <p className="tenant-empty-title">Support, opportunities, and backup risk</p>
            <p>
              Dedicated tabs for support trends, pipeline, and integration-backed service risk are planned (see{" "}
              <code style={{ fontSize: "0.85rem" }}>docs/TENANT_PRODUCT_WIREFRAMES.md</code>). This page already centralises
              scores, recommendations, and operational counts for account reviews.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
