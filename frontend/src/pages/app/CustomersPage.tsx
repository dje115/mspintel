import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import type { CustomerListResponse } from "../../api/types";
import { ScoreMeter } from "../../components/ScoreMeter";
import { useSession } from "../../state/session";

function statusBadge(status: string): string {
  if (status === "active") return "tenant-badge tenant-badge--active";
  if (status === "watch") return "tenant-badge tenant-badge--watch";
  if (status === "at_risk") return "tenant-badge tenant-badge--at_risk";
  return "tenant-badge tenant-badge--muted";
}

export function CustomersPage() {
  const { accessToken, currentTenantId } = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(() => searchParams.get("status") ?? "");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<CustomerListResponse | null>(null);

  useEffect(() => {
    const q = searchParams.get("status");
    setStatus(q ?? "");
  }, [searchParams]);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api
      .customers(accessToken, currentTenantId, {
        page,
        page_size: 12,
        search: search || undefined,
        status: status || undefined
      })
      .then(setData);
  }, [accessToken, currentTenantId, page, search, status]);

  const setStatusFilter = (value: string) => {
    setPage(1);
    setStatus(value);
    if (value) setSearchParams({ status: value }, { replace: true });
    else setSearchParams({}, { replace: true });
  };

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / 12));

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Accounts &amp; customers</h1>
        <p className="tenant-page-sub">
          Managed organisations with health scores and suggested next actions. Use filters to focus on watch-list or
          at-risk accounts.
        </p>
      </header>

      <div className="tenant-toolbar">
        <input
          className="tenant-input"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          placeholder="Search by account name…"
          aria-label="Search customers"
        />
        <select
          className="tenant-select"
          style={{ minWidth: "11rem" }}
          value={status}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="watch">Needs attention</option>
          <option value="at_risk">At risk</option>
        </select>
      </div>

      <section className="tenant-panel">
        <div className="tenant-panel-body">
          {!data ? (
            <div className="tenant-skeleton">Loading accounts…</div>
          ) : data.items.length === 0 ? (
            <div className="tenant-empty">
              <p className="tenant-empty-title">No accounts match this view</p>
              <p>Adjust search or filters, or seed demo data from the backend seed script.</p>
            </div>
          ) : (
            <div className="tenant-table-wrap">
              <table className="tenant-table">
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Status</th>
                    <th>Owner</th>
                    <th>Health</th>
                    <th>Next action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <Link to={`/app/customers/${c.id}`}>{c.name}</Link>
                      </td>
                      <td>
                        <span className={statusBadge(c.status)}>{c.status.split("_").join(" ")}</span>
                      </td>
                      <td style={{ color: "#64748b" }}>{c.owner_name ?? "—"}</td>
                      <td>
                        <div style={{ display: "grid", gap: "0.35rem", minWidth: "140px" }}>
                          <ScoreMeter label="Risk" value={c.risk_score} variant="risk" />
                          <ScoreMeter label="Attention" value={c.attention_score} />
                          <ScoreMeter label="Growth" value={c.growth_score} />
                        </div>
                      </td>
                      <td style={{ maxWidth: "16rem", color: "#475569", fontSize: "0.86rem" }}>
                        {c.next_best_action ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {data && data.items.length > 0 ? (
          <div className="tenant-pagination">
            <button type="button" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              Previous
            </button>
            <span>
              Page {page} of {totalPages} · {data.total} accounts
            </span>
            <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
