import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AIProviderCatalogRow } from "../../api/types";
import { useSession } from "../../state/session";

export function PlatformAiProvidersPage() {
  const { accessToken, authMode } = useSession();
  const [rows, setRows] = useState<AIProviderCatalogRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || authMode !== "platform") return;
    setError(null);
    try {
      const data = await api.platformAiProviderCatalog(accessToken);
      setRows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load catalog");
    }
  }, [accessToken, authMode]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <header style={{ marginBottom: "1rem" }}>
        <h1 style={{ fontSize: "1.35rem", margin: 0 }}>AI provider catalog</h1>
        <p className="muted" style={{ marginTop: "0.35rem", maxWidth: "720px" }}>
          Canonical list of provider families and deployment modes shown to MSP tenants when they configure engines.
          Credentials stay on tenant provider rows; this catalog is non-secret metadata.
        </p>
      </header>

      <div
        style={{
          marginBottom: "1rem",
          padding: "0.75rem 1rem",
          borderLeft: "4px solid #c27803",
          background: "rgba(255,255,255,0.04)"
        }}
      >
        <strong>Operational note</strong>
        <p className="muted" style={{ margin: "0.35rem 0 0" }}>
          Adding catalog entries changes what tenants can pick in the UI. Coordinate with documentation and support
          before shipping new vendor families.
        </p>
      </div>

      {error ? <p style={{ color: "#f97066" }}>{error}</p> : null}

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
              <th style={{ padding: "0.5rem 0.25rem" }}>Code</th>
              <th>Family</th>
              <th>Deployment</th>
              <th>Display name</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <td style={{ padding: "0.45rem 0.25rem" }}>
                  <code>{r.code}</code>
                </td>
                <td>{r.provider_family}</td>
                <td>{r.deployment_mode.replace(/_/g, " ")}</td>
                <td>{r.display_name}</td>
                <td className="muted">{r.description ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
