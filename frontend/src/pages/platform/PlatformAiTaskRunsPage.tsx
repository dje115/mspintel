import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AITaskRunRow } from "../../api/types";
import { useSession } from "../../state/session";

export function PlatformAiTaskRunsPage() {
  const { accessToken, authMode } = useSession();
  const [rows, setRows] = useState<AITaskRunRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || authMode !== "platform") return;
    setError(null);
    try {
      setRows(await api.platformAiTaskRuns(accessToken, 100));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load runs");
    }
  }, [accessToken, authMode]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <header style={{ marginBottom: "1rem" }}>
        <h1 style={{ fontSize: "1.35rem", margin: 0 }}>AI task runs</h1>
        <p className="muted" style={{ marginTop: "0.35rem", maxWidth: "760px" }}>
          Recent executions across tenants (read-only). Use for debugging lineage: provider, model, prompt version,
          and status. Secrets are never stored here.
        </p>
      </header>
      {error ? <p style={{ color: "#f97066" }}>{error}</p> : null}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
              <th style={{ padding: "0.45rem 0.25rem" }}>When</th>
              <th>Tenant</th>
              <th>Task</th>
              <th>Status</th>
              <th>Provider</th>
              <th>Model</th>
              <th>FB</th>
              <th>Err / out</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <td style={{ padding: "0.4rem 0.25rem", whiteSpace: "nowrap" }}>
                  {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                </td>
                <td>
                  <code>{r.tenant_id.slice(0, 8)}…</code>
                </td>
                <td>{r.task_type}</td>
                <td>{r.status}</td>
                <td>{r.provider_family ?? "—"}</td>
                <td className="muted">{r.model_used ?? "—"}</td>
                <td>{r.fallback_used ? "yes" : ""}</td>
                <td className="muted" style={{ maxWidth: "18rem" }}>
                  {r.error_summary ?? r.output_summary ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
