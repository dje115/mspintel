import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { PromptDetailResponse } from "../../api/types";
import { useSession } from "../../state/session";

export function PlatformPromptsPage() {
  const { accessToken, authMode } = useSession();
  const [rows, setRows] = useState<PromptDetailResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || authMode !== "platform") return;
    setError(null);
    try {
      const data = await api.platformListPrompts(accessToken);
      setRows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load prompts");
    }
  }, [accessToken, authMode]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <header style={{ marginBottom: "1rem" }}>
        <h1 style={{ fontSize: "1.35rem", margin: 0 }}>Global default prompts</h1>
        <p className="muted" style={{ marginTop: "0.35rem", maxWidth: "760px" }}>
          Platform-owned definitions and version history. Tenants inherit the active version unless they create an
          override. Use the API to add versions or change activation when rolling out template updates.
        </p>
      </header>

      <div
        style={{
          marginBottom: "1rem",
          padding: "0.75rem 1rem",
          borderLeft: "4px solid #f97066",
          background: "rgba(255,255,255,0.04)"
        }}
      >
        <strong>Prompt changes are high impact</strong>
        <p className="muted" style={{ margin: "0.35rem 0 0" }}>
          Publishing a new active version affects every tenant that does not override this key. Test in staging, keep
          change notes meaningful, and coordinate rollback if regressions appear.
        </p>
      </div>

      {error ? <p style={{ color: "#f97066" }}>{error}</p> : null}

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
              <th style={{ padding: "0.5rem 0.25rem" }}>Key</th>
              <th>Task</th>
              <th>Active #</th>
              <th>Versions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.definition_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <td style={{ padding: "0.45rem 0.25rem" }}>
                  <code>{r.prompt_key}</code>
                </td>
                <td>{r.task_type}</td>
                <td>{r.active_version?.version_number ?? "—"}</td>
                <td>{r.versions.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
