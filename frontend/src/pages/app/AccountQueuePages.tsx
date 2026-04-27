import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { RiskQueueResponse } from "../../api/types";
import { ScoreMeter } from "../../components/ScoreMeter";
import { useSession } from "../../state/session";

const PAGE_SIZE = 20;

function statusBadge(status: string): string {
  if (status === "active") return "tenant-badge tenant-badge--active";
  if (status === "watch") return "tenant-badge tenant-badge--watch";
  if (status === "at_risk") return "tenant-badge tenant-badge--at_risk";
  return "tenant-badge tenant-badge--muted";
}

type QueueMode = "at_risk" | "watch";

function AccountQueuePage(props: { mode: QueueMode; title: string; subtitle: string }) {
  const { accessToken, currentTenantId } = useSession();
  const { mode, title, subtitle } = props;
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [owner, setOwner] = useState("");
  const [data, setData] = useState<RiskQueueResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadError(null);
    void api
      .riskQueue(accessToken, currentTenantId, {
        mode: mode === "at_risk" ? "at_risk" : "attention",
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        owner: owner || undefined
      })
      .then(setData)
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Unable to load accounts");
      });
  }, [accessToken, currentTenantId, page, mode, search, owner]);

  if (loadError) {
    return (
      <div className="tenant-page-head">
        <h1 className="tenant-page-title">{title}</h1>
        <p className="tenant-error">{loadError}</p>
      </div>
    );
  }

  if (!data) {
    return <div className="tenant-skeleton">Loading accounts…</div>;
  }

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">{title}</h1>
        <p className="tenant-page-sub">{subtitle}</p>
      </header>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
            <input
              className="tenant-input"
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search account"
              aria-label="Search accounts"
            />
            <input
              className="tenant-input"
              value={owner}
              onChange={(e) => {
                setPage(1);
                setOwner(e.target.value);
              }}
              placeholder="Filter owner"
              aria-label="Filter owner"
            />
          </div>
          <button
            type="button"
            className="tenant-btn-inline tenant-btn-inline--ghost"
            disabled={refreshing}
            onClick={() => {
              if (!accessToken || !currentTenantId) return;
              setRefreshing(true);
              void api
                .recomputeRiskEngine(accessToken, currentTenantId)
                .then(() =>
                  api.riskQueue(accessToken, currentTenantId, {
                    mode: mode === "at_risk" ? "at_risk" : "attention",
                    page,
                    page_size: PAGE_SIZE,
                    search: search || undefined,
                    owner: owner || undefined
                  })
                )
                .then(setData)
                .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Unable to refresh risk queue"))
                .finally(() => setRefreshing(false));
            }}
          >
            {refreshing ? "Refreshing..." : "Recompute risk signals"}
          </button>
        </div>
        <div className="tenant-panel-body">
          {data.items.length === 0 ? (
            <div className="tenant-empty">
              <p className="tenant-empty-title">No accounts in this queue</p>
              <p>Scores and rules will populate this view as data grows.</p>
            </div>
          ) : (
            <div className="tenant-table-wrap">
              <table className="tenant-table">
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Status</th>
                    {mode === "at_risk" ? <th>Risk</th> : <th>Attention</th>}
                    <th>Signal</th>
                    <th>Owner</th>
                    <th>Why / next</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((c) => (
                    <tr key={c.customer_id}>
                      <td>
                        <Link to={mode === "at_risk" ? `/app/customers/${c.customer_id}?ai=risk` : `/app/customers/${c.customer_id}`}>{c.customer_name}</Link>
                      </td>
                      <td>
                        <span className={statusBadge(c.status)}>{c.status.replace("_", " ")}</span>
                      </td>
                      <td>{mode === "at_risk" ? c.risk_score : c.attention_score}</td>
                      <td>
                        <ScoreMeter
                          label=" "
                          value={mode === "at_risk" ? c.risk_score : c.attention_score}
                          variant={mode === "at_risk" ? "risk" : undefined}
                        />
                      </td>
                      <td>{c.owner_name ?? "—"}</td>
                      <td className="muted" style={{ maxWidth: "18rem" }}>
                        {c.top_reasons.length > 0 ? c.top_reasons.join(" | ") : c.next_step_placeholder}
                      </td>
                      <td>
                        <Link className="tenant-btn-inline" to={`/app/customers/${c.customer_id}#workspace`}>
                          Open 360
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {totalPages > 1 ? (
        <div className="tenant-pagination tenant-page-tail">
          <button type="button" className="tenant-btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="muted">
            Page {page} of {totalPages} ({data.total} accounts)
          </span>
          <button
            type="button"
            className="tenant-btn-ghost"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function AtRiskAccountsPage() {
  return (
    <AccountQueuePage
      mode="at_risk"
      title="At-risk accounts"
      subtitle="Accounts with elevated churn or delivery risk. Work the list top-down and link into each account workspace."
    />
  );
}

export function NeedsAttentionAccountsPage() {
  return (
    <AccountQueuePage
      mode="watch"
      title="Needs attention"
      subtitle="Watch-list accounts that merit proactive outreach before issues compound."
    />
  );
}
