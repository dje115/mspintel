import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import type { CommercialHubResponse, OpportunityRow, QuoteRow } from "../../api/types";
import { useSession } from "../../state/session";
import { formatShortDate, formatUsdFromCents } from "../../utils/formatWorkspace";

type Tab = "opportunities" | "lost" | "pipeline";

function RowActions({ customerId }: { customerId: string }) {
  return (
    <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", justifyContent: "flex-end" }}>
      <Link className="tenant-btn-inline" to={`/app/customers/${customerId}`}>
        Account
      </Link>
      <Link className="tenant-btn-inline tenant-btn-inline--ghost" to={`/app/customers/${customerId}#workspace`}>
        360
      </Link>
    </div>
  );
}

function OpportunitiesTable({ rows }: { rows: OpportunityRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="tenant-empty">
        <p className="tenant-empty-title">No open opportunities</p>
        <p>PSA-sourced opportunities will land here for commercial follow-up.</p>
      </div>
    );
  }
  return (
    <div className="tenant-table-wrap">
      <table className="tenant-table">
        <thead>
          <tr>
            <th>Account</th>
            <th>Title</th>
            <th>Value</th>
            <th>Status</th>
            <th>Opened</th>
            <th>Next action</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.id}>
              <td>
                <Link to={`/app/customers/${o.customer_id}`}>{o.customer_name ?? "—"}</Link>
              </td>
              <td>{o.title}</td>
              <td>{formatUsdFromCents(o.value_cents)}</td>
              <td>
                <span className="tenant-badge tenant-badge--active">{o.status}</span>
              </td>
              <td>{formatShortDate(o.created_at)}</td>
              <td className="muted" style={{ maxWidth: "14rem" }}>
                {o.suggested_next_action}
              </td>
              <td>
                <RowActions customerId={o.customer_id} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function QuotesTable({ rows, variant }: { rows: QuoteRow[]; variant: "lost" | "open" }) {
  if (rows.length === 0) {
    return (
      <div className="tenant-empty">
        <p className="tenant-empty-title">{variant === "lost" ? "No lost quotes flagged" : "No draft or open quotes"}</p>
        <p>Quotes sync from PSA; lost rows are prioritised for revisit campaigns.</p>
      </div>
    );
  }
  return (
    <div className="tenant-table-wrap">
      <table className="tenant-table">
        <thead>
          <tr>
            <th>Account</th>
            <th>Title</th>
            <th>Value</th>
            <th>Status</th>
            <th>Date</th>
            <th>Reason / signal</th>
            <th>Next action</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((q) => (
            <tr key={q.id}>
              <td>
                <Link to={`/app/customers/${q.customer_id}`}>{q.customer_name ?? "—"}</Link>
              </td>
              <td>{q.title}</td>
              <td>{formatUsdFromCents(q.value_cents)}</td>
              <td>
                <span className={`tenant-badge ${variant === "lost" ? "tenant-badge--at_risk" : "tenant-badge--watch"}`}>
                  {q.status}
                </span>
              </td>
              <td>{formatShortDate(q.created_at)}</td>
              <td className="muted" style={{ maxWidth: "14rem" }}>
                {q.revisit_reason ?? "—"}
              </td>
              <td className="muted" style={{ maxWidth: "12rem" }}>
                {q.suggested_next_action}
              </td>
              <td>
                <RowActions customerId={q.customer_id} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function OpportunitiesPage() {
  const { accessToken, currentTenantId } = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = (searchParams.get("tab") as Tab | null) ?? "opportunities";
  const safeTab: Tab = tab === "lost" || tab === "pipeline" ? tab : "opportunities";

  const [data, setData] = useState<CommercialHubResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadError(null);
    void api
      .workspaceCommercial(accessToken, currentTenantId)
      .then(setData)
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Unable to load commercial hub");
      });
  }, [accessToken, currentTenantId]);

  const setTab = (next: Tab) => {
    const qs = new URLSearchParams(searchParams);
    qs.set("tab", next);
    setSearchParams(qs, { replace: true });
  };

  if (loadError) {
    return (
      <div className="tenant-page-head">
        <h1 className="tenant-page-title">Opportunities</h1>
        <p className="tenant-error">{loadError}</p>
      </div>
    );
  }

  if (!data) {
    return <div className="tenant-skeleton">Loading commercial hub…</div>;
  }

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Opportunities &amp; quotes</h1>
        <p className="tenant-page-sub">
          New pipeline, active quotes, and <strong>lost quotes worth revisiting</strong> in one commercial workspace.
        </p>
      </header>

      <div className="tenant-segmented" role="tablist" aria-label="Commercial views">
        <button type="button" className={`tenant-segment${safeTab === "opportunities" ? " is-active" : ""}`} onClick={() => setTab("opportunities")}>
          New opportunities
          <span className="tenant-segment-count">{data.opportunities.length}</span>
        </button>
        <button type="button" className={`tenant-segment${safeTab === "pipeline" ? " is-active" : ""}`} onClick={() => setTab("pipeline")}>
          Open &amp; draft quotes
          <span className="tenant-segment-count">{data.open_quotes.length}</span>
        </button>
        <button type="button" className={`tenant-segment${safeTab === "lost" ? " is-active" : ""}`} onClick={() => setTab("lost")}>
          Lost quotes — revisit
          <span className="tenant-segment-count">{data.lost_quotes.length}</span>
        </button>
      </div>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">
            {safeTab === "opportunities" ? "Discovered opportunities" : safeTab === "pipeline" ? "Active quote pipeline" : "Dormant / lost quotes"}
          </h2>
        </div>
        <div className="tenant-panel-body">
          {safeTab === "opportunities" ? (
            <OpportunitiesTable rows={data.opportunities} />
          ) : safeTab === "pipeline" ? (
            <QuotesTable rows={data.open_quotes} variant="open" />
          ) : (
            <QuotesTable rows={data.lost_quotes} variant="lost" />
          )}
        </div>
      </section>
    </div>
  );
}
