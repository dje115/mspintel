import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { CustomerListResponse } from "../../api/types";
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
  const [data, setData] = useState<CustomerListResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadError(null);
    void api
      .customers(accessToken, currentTenantId, {
        page,
        page_size: PAGE_SIZE,
        status: mode
      })
      .then(setData)
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Unable to load accounts");
      });
  }, [accessToken, currentTenantId, page, mode]);

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
                    <tr key={c.id}>
                      <td>
                        <Link to={`/app/customers/${c.id}`}>{c.name}</Link>
                      </td>
                      <td>
                        <span className={statusBadge(c.status)}>{c.status.replace("_", " ")}</span>
                      </td>
                      <td>{mode === "at_risk" ? (c.risk_score ?? "—") : (c.attention_score ?? "—")}</td>
                      <td>
                        <ScoreMeter
                          label=" "
                          value={mode === "at_risk" ? c.risk_score : c.attention_score}
                          variant={mode === "at_risk" ? "risk" : undefined}
                        />
                      </td>
                      <td>{c.owner_name ?? "—"}</td>
                      <td className="muted" style={{ maxWidth: "18rem" }}>
                        {c.next_best_action ?? "—"}
                      </td>
                      <td>
                        <Link className="tenant-btn-inline" to={`/app/customers/${c.id}#workspace`}>
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
        <div className="tenant-pagination">
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
