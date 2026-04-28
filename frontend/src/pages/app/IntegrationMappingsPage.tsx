import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { CustomerListItem, MappingReviewRow, SourceConnection } from "../../api/types";
import { useSession } from "../../state/session";

export function IntegrationMappingsPage() {
  const { accessToken, currentTenantId } = useSession();
  const [rows, setRows] = useState<MappingReviewRow[]>([]);
  const [connections, setConnections] = useState<SourceConnection[]>([]);
  const [customers, setCustomers] = useState<CustomerListItem[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    const [mappingRows, connectionRows, customerRows] = await Promise.all([
      api.integrationMappings(accessToken, currentTenantId),
      api.integrations(accessToken, currentTenantId),
      api.customers(accessToken, currentTenantId, { page: 1, page_size: 100 }),
    ]);
    setRows(mappingRows);
    setConnections(connectionRows);
    setCustomers(customerRows.items);
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    void load().catch((e: unknown) => setErr(e instanceof Error ? e.message : "Failed to load mapping queue"));
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
            Connected systems: {connections.length} · Pending reviews: {rows.filter((r) => r.status === "pending").length}
          </p>
          <div className="tenant-table-wrap">
            <table className="tenant-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Record</th>
                  <th>Suggestion</th>
                  <th>Status</th>
                  <th>Override</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.source_connection_name ?? r.source_connection_id}</td>
                    <td>
                      {r.source_display_name ?? r.source_external_id}
                      <div className="muted" style={{ fontSize: "0.8rem" }}>
                        {r.source_external_id}
                      </div>
                    </td>
                    <td>
                      <span className="tenant-badge tenant-badge--watch">{r.suggested_confidence}</span>{" "}
                      {r.suggested_customer_name ?? "No suggestion"}
                      <div className="muted" style={{ fontSize: "0.8rem" }}>
                        {(r.suggested_reasons || []).join(", ") || "insufficient signals"}
                      </div>
                    </td>
                    <td>{r.status}</td>
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
                      <button type="button" className="tenant-btn-ghost" onClick={() => void act(r.id, "accept", r.suggested_customer_id ?? undefined)}>
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

