import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../../api/client";
import type { CustomerListItem, MappingReviewRow, SourceConnection } from "../../api/types";
import { useSession } from "../../state/session";

export function IntegrationMappingsPage() {
  const { accessToken, currentTenantId } = useSession();
  const [rows, setRows] = useState<MappingReviewRow[]>([]);
  const [connections, setConnections] = useState<SourceConnection[]>([]);
  const [customers, setCustomers] = useState<CustomerListItem[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Record<string, string>>({});
  const [selectedConnection, setSelectedConnection] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [selectedConfidence, setSelectedConfidence] = useState<string>("");
  const [selectedCustomerFilter, setSelectedCustomerFilter] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    setLoading(true);
    setErr(null);
    const [mappingRows, connectionRows, customerRows] = await Promise.all([
      api.integrationMappings(accessToken, currentTenantId, {
        connection_id: selectedConnection || undefined,
        status_filter: selectedStatus || undefined,
        confidence: selectedConfidence || undefined,
        search: search.trim() || undefined,
        customer_id: selectedCustomerFilter || undefined
      }),
      api.integrations(accessToken, currentTenantId),
      api.customers(accessToken, currentTenantId, { page: 1, page_size: 100 }),
    ]);
    setRows(mappingRows);
    setConnections(connectionRows);
    setCustomers(customerRows.items);
    setLoading(false);
  }, [accessToken, currentTenantId, search, selectedConfidence, selectedConnection, selectedCustomerFilter, selectedStatus]);

  useEffect(() => {
    void load().catch((e: unknown) => {
      setLoading(false);
      setErr(e instanceof Error ? e.message : "Failed to load mapping queue");
    });
  }, [load]);

  const act = async (id: string, action: string, customerId?: string) => {
    if (!accessToken || !currentTenantId) return;
    try {
      await api.integrationMappingAction(accessToken, currentTenantId, id, { action, customer_id: customerId });
      await load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Mapping action failed");
    }
  };

  const counts = useMemo(() => {
    const all = rows.length;
    const pending = rows.filter((r) => r.status === "pending").length;
    const confirmed = rows.filter((r) => r.status === "accepted" || r.status === "remapped").length;
    const rejected = rows.filter((r) => r.status === "rejected").length;
    const unlinked = rows.filter((r) => r.status === "unlinked").length;
    return { all, pending, confirmed, rejected, unlinked };
  }, [rows]);

  const toneForStatus = (status: string) => {
    if (status === "pending") return "tenant-badge tenant-badge--watch";
    if (status === "accepted" || status === "remapped") return "tenant-badge tenant-badge--active";
    if (status === "rejected") return "tenant-badge tenant-badge--at_risk";
    return "tenant-badge tenant-badge--muted";
  };

  const confidenceLabel = (row: MappingReviewRow) => {
    if (row.status === "pending") {
      if (row.suggested_confidence === "low") return "Low confidence";
      return "Suggested";
    }
    if (row.status === "accepted" || row.status === "remapped") return "Confirmed";
    if (row.status === "rejected") return "Rejected";
    return "Unlinked";
  };

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Integration mappings review</h1>
        <p className="tenant-page-sub">Review suggested matches, override manually, and keep cross-system identity clean.</p>
      </header>
      {err ? <p className="tenant-error">{err}</p> : null}
      <section className="tenant-panel">
        <div className="tenant-panel-body">
          <p className="muted" style={{ marginTop: 0 }}>
            Connected systems: {connections.length} · Needs review: {counts.pending} · Confirmed: {counts.confirmed} ·
            Rejected: {counts.rejected} · Unlinked: {counts.unlinked}
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(12rem,1fr))", gap: "0.6rem", marginBottom: "0.75rem" }}>
            <select className="tenant-select" value={selectedConnection} onChange={(e) => setSelectedConnection(e.target.value)}>
              <option value="">All connectors</option>
              {connections.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.display_name}
                </option>
              ))}
            </select>
            <select className="tenant-select" value={selectedStatus} onChange={(e) => setSelectedStatus(e.target.value)}>
              <option value="">All statuses</option>
              <option value="pending">Needs review</option>
              <option value="accepted,remapped">Confirmed</option>
              <option value="rejected">Rejected</option>
              <option value="unlinked">Unlinked</option>
            </select>
            <select className="tenant-select" value={selectedConfidence} onChange={(e) => setSelectedConfidence(e.target.value)}>
              <option value="">All confidence levels</option>
              <option value="high">High confidence</option>
              <option value="medium">Suggested</option>
              <option value="low">Low confidence</option>
            </select>
            <select className="tenant-select" value={selectedCustomerFilter} onChange={(e) => setSelectedCustomerFilter(e.target.value)}>
              <option value="">All customers</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <input
              className="tenant-input"
              placeholder="Search source name, id, or domain"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {loading ? <p className="tenant-skeleton">Loading mapping review queue…</p> : null}
          {!loading && rows.length === 0 ? (
            <p className="tenant-page-sub" style={{ marginTop: "0.55rem" }}>
              No mappings match this filter. Suggested mappings appear here as <strong>Needs review</strong>. Run a connector sync or
              widen filters to review candidates.
            </p>
          ) : null}
          <div className="tenant-table-wrap">
            <table className="tenant-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Record</th>
                  <th>Suggestion</th>
                  <th>Status</th>
                  <th>Last sync</th>
                  <th>Override</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>
                      {r.source_connection_name ?? r.source_connection_id}
                      <div className="muted" style={{ fontSize: "0.8rem" }}>
                        <span className="tenant-badge tenant-badge--muted">{r.source_system_key ?? "connector"}</span>
                      </div>
                    </td>
                    <td>
                      {r.source_display_name ?? r.source_external_id}
                      <div className="muted" style={{ fontSize: "0.8rem" }}>
                        {r.entity_type} · {r.source_external_id}
                      </div>
                    </td>
                    <td>
                      <span className={toneForStatus(r.status)}>{confidenceLabel(r)}</span>{" "}
                      {r.suggested_customer_name ?? "No suggestion"}
                      <div className="muted" style={{ fontSize: "0.8rem" }}>
                        {(r.suggested_reasons || []).join(", ") || "insufficient signals"}
                      </div>
                    </td>
                    <td>
                      <span className={toneForStatus(r.status)}>{r.status_label ?? r.status}</span>
                    </td>
                    <td>
                      {r.last_sync_started_at ? new Date(r.last_sync_started_at).toLocaleString() : "No sync reference"}
                      <div className="muted" style={{ fontSize: "0.8rem" }}>{r.last_sync_status ?? "unknown"}</div>
                    </td>
                    <td>
                      <select
                        className="tenant-select"
                        value={selectedCustomer[r.id] ?? ""}
                        onChange={(e) => setSelectedCustomer((prev) => ({ ...prev, [r.id]: e.target.value }))}
                      >
                        <option value="">Select customer</option>
                        {customers.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="tenant-btn-ghost"
                        onClick={() => void act(r.id, "accept", r.suggested_customer_id ?? undefined)}
                        disabled={!r.suggested_customer_id}
                        title={!r.suggested_customer_id ? "No suggested customer to accept" : undefined}
                      >
                        Accept
                      </button>{" "}
                      <button
                        type="button"
                        className="tenant-btn-ghost"
                        onClick={() => void act(r.id, "remap", selectedCustomer[r.id])}
                        disabled={!selectedCustomer[r.id]}
                      >
                        Remap
                      </button>{" "}
                      <button type="button" className="tenant-btn-ghost" onClick={() => void act(r.id, "reject")}>
                        Reject
                      </button>{" "}
                      <button type="button" className="tenant-btn-ghost" onClick={() => void act(r.id, "unlink")}>
                        Unlink
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

