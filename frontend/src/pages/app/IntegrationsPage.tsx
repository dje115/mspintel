import { useEffect, useState } from "react";

import { api } from "../../api/client";
import type { SourceConnection } from "../../api/types";
import { useSession } from "../../state/session";

export function IntegrationsPage() {
  const { accessToken, currentTenantId } = useSession();
  const [rows, setRows] = useState<SourceConnection[]>([]);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api.integrations(accessToken, currentTenantId).then(setRows);
  }, [accessToken, currentTenantId]);

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Integrations</h1>
        <p className="tenant-page-sub">
          Connect PSA, RMM, Microsoft 365, and other sources so scores, recommendations, and risk signals stay current.
        </p>
      </header>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Connections</h2>
        </div>
        <div className="tenant-panel-body">
          {rows.length === 0 ? (
            <div className="tenant-empty">
              <p className="tenant-empty-title">No integrations yet</p>
              <p>
                When connectors are enabled for your plan, authorised admins can add systems here. Until then, demo data
                powers the customer workspace.
              </p>
            </div>
          ) : (
            <div className="tenant-table-wrap">
              <table className="tenant-table">
                <thead>
                  <tr>
                    <th>System</th>
                    <th>Display name</th>
                    <th>Status</th>
                    <th>Last sync</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id}>
                      <td>{row.system_type}</td>
                      <td>{row.display_name}</td>
                      <td>
                        <span className="tenant-badge tenant-badge--muted">{row.status}</span>
                      </td>
                      <td style={{ color: "#64748b" }}>{row.last_sync_at ?? "—"}</td>
                      <td>
                        <button type="button" className="tenant-btn-ghost" disabled>
                          Test
                        </button>{" "}
                        <button type="button" className="tenant-btn-ghost" disabled>
                          Sync
                        </button>
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
  );
}
