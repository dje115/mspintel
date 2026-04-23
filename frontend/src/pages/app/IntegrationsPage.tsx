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
    <div className="stack">
      <h1>Integrations</h1>
      <p>Source system cards are scaffolded for connector onboarding and sync operations.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>System Type</th>
              <th>Display Name</th>
              <th>Status</th>
              <th>Last Sync</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.system_type}</td>
                <td>{row.display_name}</td>
                <td>{row.status}</td>
                <td>{row.last_sync_at ?? "-"}</td>
                <td>
                  <button>Test Connection</button>
                  <button>Sync Now</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
