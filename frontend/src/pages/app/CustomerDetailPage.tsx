import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { api } from "../../api/client";
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
  const { accessToken, currentTenantId } = useSession();
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
