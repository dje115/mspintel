import { Fragment, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import type { CustomerListResponse, RecommendationListResponse } from "../../api/types";
import { useSession } from "../../state/session";
import { formatAge, formatShortDate } from "../../utils/formatWorkspace";
import { TenantAiContextNotice } from "../../components/TenantAiContextNotice";

const PAGE_SIZE = 15;

function priorityClass(p: string): string {
  if (p === "high") return "tenant-badge tenant-badge--at_risk";
  if (p === "medium") return "tenant-badge tenant-badge--watch";
  return "tenant-badge tenant-badge--muted";
}

export function RecommendationsPage() {
  const { accessToken, currentTenantId, me } = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<RecommendationListResponse | null>(null);
  const [customers, setCustomers] = useState<CustomerListResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [aiExplainBusy, setAiExplainBusy] = useState<Record<string, boolean>>({});
  const [aiExplainText, setAiExplainText] = useState<Record<string, string>>({});
  const [aiExplainErr, setAiExplainErr] = useState<Record<string, string | undefined>>({});
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const status = searchParams.get("status") ?? "";
  const scope = searchParams.get("scope") ?? "";
  const customerId = searchParams.get("customer_id") ?? "";
  const [ownerFilter, setOwnerFilter] = useState("");

  const isTenantAdmin = useMemo(
    () => me?.memberships.some((m) => m.tenant_id === currentTenantId && m.role_code === "tenant_admin"),
    [me, currentTenantId]
  );

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api
      .customers(accessToken, currentTenantId, { page: 1, page_size: 100 })
      .then(setCustomers)
      .catch(() => setCustomers(null));
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadError(null);
    void api
      .workspaceRecommendations(accessToken, currentTenantId, {
        page,
        page_size: PAGE_SIZE,
        status: status || undefined,
        scope: scope || undefined,
        owner: ownerFilter || undefined,
        customer_id: customerId || undefined
      })
      .then(setData)
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Unable to load recommendations");
      });
  }, [accessToken, currentTenantId, page, status, scope, ownerFilter, customerId]);

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("page");
    setSearchParams(next, { replace: true });
    setPage(1);
  };

  const generateExplanation = async (recId: string) => {
    if (!accessToken || !currentTenantId) return;
    setAiExplainBusy((m) => ({ ...m, [recId]: true }));
    setAiExplainErr((m) => ({ ...m, [recId]: undefined }));
    try {
      const out = await api.postRecommendationExplanationAi(accessToken, currentTenantId, recId);
      if (out.status === "succeeded" && out.text) {
        setAiExplainText((m) => ({ ...m, [recId]: out.text ?? "" }));
        setAiExplainErr((m) => ({ ...m, [recId]: undefined }));
      } else {
        const fallback =
          out.message ??
          (out.status === "unsupported"
            ? "This provider family is not executable in this release."
            : out.status === "unavailable"
              ? "AI is not fully configured for this task (provider, model, or active prompt)."
              : out.status === "skipped"
                ? "This AI task is disabled for your tenant."
                : out.status === "failed"
                  ? "Generation failed — check tenant AI settings and provider credentials."
                  : `AI returned status: ${out.status}`);
        setAiExplainErr((m) => ({ ...m, [recId]: fallback }));
        setAiExplainText((m) => {
          const next = { ...m };
          delete next[recId];
          return next;
        });
      }
    } catch (e: unknown) {
      setAiExplainErr((m) => ({ ...m, [recId]: e instanceof Error ? e.message : "AI request failed" }));
    } finally {
      setAiExplainBusy((m) => ({ ...m, [recId]: false }));
    }
  };

  const syncFromSignals = async () => {
    if (!accessToken || !currentTenantId) return;
    setSyncBusy(true);
    setSyncMessage(null);
    setActionError(null);
    try {
      const out = await api.syncRecommendationsFromSignals(accessToken, currentTenantId);
      setSyncMessage(`Synced: +${out.created} new, ${out.updated} updated, ${out.completed} completed.`);
      const refreshed = await api.workspaceRecommendations(accessToken, currentTenantId, {
        page,
        page_size: PAGE_SIZE,
        status: status || undefined,
        scope: scope || undefined,
        owner: ownerFilter || undefined,
        customer_id: customerId || undefined
      });
      setData(refreshed);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncBusy(false);
    }
  };

  const patchStatus = async (id: string, next: string) => {
    if (!accessToken || !currentTenantId) return;
    setActionError(null);
    try {
      await api.patchRecommendation(accessToken, currentTenantId, id, next);
      const refreshed = await api.workspaceRecommendations(accessToken, currentTenantId, {
        page,
        page_size: PAGE_SIZE,
        status: status || undefined,
        scope: scope || undefined,
        owner: ownerFilter || undefined,
        customer_id: customerId || undefined
      });
      setData(refreshed);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Update failed");
    }
  };

  if (loadError) {
    return (
      <div className="tenant-page-head">
        <h1 className="tenant-page-title">Recommendations</h1>
        <p className="tenant-error">{loadError}</p>
      </div>
    );
  }

  if (!data) {
    return <div className="tenant-skeleton">Loading recommendations…</div>;
  }

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const openCount = data.items.filter((r) => r.status === "open").length;

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Recommendations</h1>
        <p className="tenant-page-sub">
          Cross-account queue of suggested next steps. {data.total > 0 ? `${data.total} in filter` : "No rows match"}{" "}
          — <strong>{openCount}</strong> open on this page.
        </p>
      </header>
      <TenantAiContextNotice compact />

      {actionError ? <p className="tenant-error">{actionError}</p> : null}
      {syncMessage ? <p className="muted" style={{ fontSize: "0.88rem" }}>{syncMessage}</p> : null}

      <div className="tenant-toolbar tenant-toolbar--wrap">
        {isTenantAdmin ? (
          <button
            type="button"
            className="tenant-btn-inline"
            disabled={syncBusy}
            onClick={() => void syncFromSignals()}
            title="Create or refresh open items from mapping, billing, tickets, quotes, and M365 signals"
          >
            {syncBusy ? "Syncing…" : "Refresh from data"}
          </button>
        ) : null}
        <select
          className="tenant-select"
          aria-label="Status"
          value={status}
          onChange={(e) => setFilter("status", e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="accepted">Accepted</option>
          <option value="rejected">Rejected</option>
          <option value="completed">Completed</option>
        </select>
        <select
          className="tenant-select"
          aria-label="Scope / category"
          value={scope}
          onChange={(e) => setFilter("scope", e.target.value)}
        >
          <option value="">All categories</option>
          <option value="executive">Executive</option>
          <option value="sales">Sales</option>
          <option value="service">Service</option>
        </select>
        <select
          className="tenant-select"
          aria-label="Account"
          value={customerId}
          onChange={(e) => setFilter("customer_id", e.target.value)}
          style={{ minWidth: "12rem" }}
        >
          <option value="">All accounts</option>
          {(customers?.items ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input
          className="tenant-input"
          style={{ maxWidth: "14rem" }}
          placeholder="Owner contains…"
          aria-label="Filter by owner"
          value={ownerFilter}
          onChange={(e) => {
            setOwnerFilter(e.target.value);
            setPage(1);
          }}
        />
      </div>

      <section className="tenant-panel">
        <div className="tenant-panel-body">
          {data.items.length === 0 ? (
            <div className="tenant-empty">
              <p className="tenant-empty-title">No recommendations match</p>
              <p>
                Adjust filters or improve data inputs. Tenant admins can use <strong>Refresh from data</strong> to
                materialise items from mapping, billing, tickets, quotes, and M365 signals. Otherwise complete
                onboarding and connect PSA, finance, and M365 so the queue stays meaningful.
              </p>
            </div>
          ) : (
            <div className="tenant-table-wrap">
              <table className="tenant-table">
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Category</th>
                    <th>Priority</th>
                    <th>Summary</th>
                    <th>Next action</th>
                    <th>Owner</th>
                    <th>Status</th>
                    <th>Age</th>
                    <th>AI</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <Fragment key={r.id}>
                    <tr>
                      <td>
                        {r.customer_id ? (
                          <Link to={`/app/customers/${r.customer_id}`}>{r.customer_name ?? "Account"}</Link>
                        ) : (
                          <span className="muted">Tenant-wide</span>
                        )}
                      </td>
                      <td>
                        <span className="tenant-badge tenant-badge--muted">{r.category}</span>
                      </td>
                      <td>
                        <span className={priorityClass(r.priority)}>{r.priority}</span>
                      </td>
                      <td style={{ maxWidth: "16rem" }}>{r.summary}</td>
                      <td className="muted" style={{ maxWidth: "12rem" }}>
                        {r.suggested_next_action}
                      </td>
                      <td>{r.owner_name ?? "—"}</td>
                      <td>
                        <span className="tenant-badge tenant-badge--muted">{r.status}</span>
                      </td>
                      <td>
                        <span title={formatShortDate(r.created_at ?? undefined)}>{formatAge(r.created_at)}</span>
                      </td>
                      <td style={{ maxWidth: "11rem", verticalAlign: "top" }}>
                        <button
                          type="button"
                          className="tenant-btn-inline tenant-btn-inline--ghost"
                          disabled={!!aiExplainBusy[r.id]}
                          onClick={() => void generateExplanation(r.id)}
                        >
                          {aiExplainBusy[r.id] ? "…" : "Explain"}
                        </button>
                      </td>
                      <td>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", justifyContent: "flex-end" }}>
                          {r.customer_id ? (
                            <Link className="tenant-btn-inline" to={`/app/customers/${r.customer_id}#workspace`}>
                              360
                            </Link>
                          ) : null}
                          {isTenantAdmin && r.status === "open" ? (
                            <>
                              <button type="button" className="tenant-btn-inline" onClick={() => void patchStatus(r.id, "accepted")}>
                                Accept
                              </button>
                              <button type="button" className="tenant-btn-inline tenant-btn-inline--ghost" onClick={() => void patchStatus(r.id, "rejected")}>
                                Reject
                              </button>
                            </>
                          ) : null}
                          {isTenantAdmin && (r.status === "accepted" || r.status === "open") ? (
                            <button type="button" className="tenant-btn-inline tenant-btn-inline--ghost" onClick={() => void patchStatus(r.id, "completed")}>
                              Done
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                    {aiExplainText[r.id] || aiExplainErr[r.id] ? (
                      <tr className="tenant-table-subrow">
                        <td colSpan={10} style={{ paddingTop: 0, borderTop: "none", background: "rgba(15, 118, 110, 0.04)" }}>
                          <div className="muted" style={{ fontSize: "0.72rem", marginBottom: "0.25rem" }}>
                            AI explanation (provider + prompt version + tenant context; quality depends on onboarding and connector coverage)
                          </div>
                          {aiExplainText[r.id] ? (
                            <div className="tenant-rec-card" style={{ fontSize: "0.88rem", whiteSpace: "pre-wrap" }}>
                              {aiExplainText[r.id]}
                            </div>
                          ) : (
                            <p className="tenant-error" style={{ fontSize: "0.88rem", margin: 0 }}>
                              {aiExplainErr[r.id]}
                            </p>
                          )}
                        </td>
                      </tr>
                    ) : null}
                    </Fragment>
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
            Page {page} of {totalPages}
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
