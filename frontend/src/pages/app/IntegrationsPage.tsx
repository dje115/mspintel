import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { ConnectorCatalogItem, IntegrationSyncRun, SourceConnection } from "../../api/types";
import { useSession } from "../../state/session";

export function IntegrationsPage() {
  const { accessToken, currentTenantId } = useSession();
  const [rows, setRows] = useState<SourceConnection[]>([]);
  const [catalog, setCatalog] = useState<ConnectorCatalogItem[]>([]);
  const [runs, setRuns] = useState<Record<string, IntegrationSyncRun[]>>({});
  const [busyById, setBusyById] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    system_type: "autotask",
    display_name: "Primary Autotask",
    base_url: "",
    username: "",
    integration_code: "",
    secret: "",
    sync_cadence_minutes: 30
  });

  const selectedCatalog = useMemo(
    () => catalog.find((c) => c.system_type === createForm.system_type) ?? null,
    [catalog, createForm.system_type]
  );

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    setErr(null);
    try {
      const [connections, providerCatalog] = await Promise.all([
        api.integrations(accessToken, currentTenantId),
        api.integrationCatalog(accessToken, currentTenantId)
      ]);
      setRows(connections);
      setCatalog(providerCatalog);
      const runPairs = await Promise.all(
        connections.map(async (c) => [c.id, await api.integrationRuns(accessToken, currentTenantId, c.id, 8)] as const)
      );
      setRuns(Object.fromEntries(runPairs));
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to load integrations");
    }
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const runAction = async (connectionId: string, action: "test" | "sync") => {
    if (!accessToken || !currentTenantId) return;
    setBusyById((m) => ({ ...m, [connectionId]: action }));
    setErr(null);
    try {
      if (action === "test") {
        await api.testIntegrationConnection(accessToken, currentTenantId, connectionId);
      } else {
        await api.syncIntegrationConnection(accessToken, currentTenantId, connectionId);
      }
      await load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyById((m) => ({ ...m, [connectionId]: "" }));
    }
  };

  const createConnection = async () => {
    if (!accessToken || !currentTenantId) return;
    setErr(null);
    try {
      await api.createIntegrationConnection(accessToken, currentTenantId, {
        system_type: createForm.system_type,
        display_name: createForm.display_name,
        base_url: createForm.base_url || null,
        auth_mode: "api_key",
        sync_cadence_minutes: createForm.sync_cadence_minutes,
        is_enabled: true,
        config:
          createForm.system_type === "autotask"
            ? {
                base_url: createForm.base_url,
                username: createForm.username,
                integration_code: createForm.integration_code,
                secret: createForm.secret
              }
            : {}
      });
      setCreateForm((v) => ({ ...v, secret: "" }));
      await load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Create failed");
    }
  };

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Integrations</h1>
        <p className="tenant-page-sub">
          Connect PSA, RMM, Microsoft 365, and other sources so scores, recommendations, and risk signals stay current.
        </p>
      </header>
      {err ? <p className="tenant-error">{err}</p> : null}

      <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Add connector</h2>
        </div>
        <div className="tenant-panel-body">
          <div className="tenant-grid tenant-grid--cards-3">
            <label>
              System
              <select
                className="tenant-select"
                value={createForm.system_type}
                onChange={(e) => setCreateForm((v) => ({ ...v, system_type: e.target.value }))}
              >
                {catalog.map((c) => (
                  <option key={c.system_type} value={c.system_type}>
                    {c.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Display name
              <input
                className="tenant-input"
                value={createForm.display_name}
                onChange={(e) => setCreateForm((v) => ({ ...v, display_name: e.target.value }))}
              />
            </label>
            <label>
              Sync cadence (minutes)
              <input
                className="tenant-input"
                type="number"
                min={5}
                value={createForm.sync_cadence_minutes}
                onChange={(e) => setCreateForm((v) => ({ ...v, sync_cadence_minutes: Number(e.target.value) || 30 }))}
              />
            </label>
          </div>
          {createForm.system_type === "autotask" ? (
            <div className="tenant-grid tenant-grid--cards-3" style={{ marginTop: "0.75rem" }}>
              <label>
                Base URL
                <input
                  className="tenant-input"
                  value={createForm.base_url}
                  onChange={(e) => setCreateForm((v) => ({ ...v, base_url: e.target.value }))}
                  placeholder="https://webservicesXX.autotask.net/ATServicesRest"
                />
              </label>
              <label>
                Username
                <input
                  className="tenant-input"
                  value={createForm.username}
                  onChange={(e) => setCreateForm((v) => ({ ...v, username: e.target.value }))}
                />
              </label>
              <label>
                Integration code
                <input
                  className="tenant-input"
                  value={createForm.integration_code}
                  onChange={(e) => setCreateForm((v) => ({ ...v, integration_code: e.target.value }))}
                />
              </label>
              <label>
                Secret
                <input
                  className="tenant-input"
                  type="password"
                  value={createForm.secret}
                  onChange={(e) => setCreateForm((v) => ({ ...v, secret: e.target.value }))}
                />
              </label>
            </div>
          ) : (
            <p className="muted" style={{ marginTop: "0.75rem" }}>
              {selectedCatalog?.display_name} is scaffolded for future phases. You can still register a placeholder connection
              to track rollout planning.
            </p>
          )}
          <div style={{ marginTop: "0.9rem" }}>
            <button type="button" className="tenant-btn-primary" onClick={() => void createConnection()}>
              Save connection
            </button>
          </div>
        </div>
      </section>

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
                    <th>Health</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <Fragment key={row.id}>
                    <tr>
                      <td>{row.system_type}</td>
                      <td>{row.display_name}</td>
                      <td>
                        <span className="tenant-badge tenant-badge--muted">{row.status}</span>
                      </td>
                      <td style={{ color: "#64748b" }}>{row.last_sync_at ?? "—"}</td>
                      <td style={{ color: "#64748b" }}>{row.health_status}</td>
                      <td>
                        <button
                          type="button"
                          className="tenant-btn-ghost"
                          disabled={!!busyById[row.id]}
                          onClick={() => void runAction(row.id, "test")}
                        >
                          {busyById[row.id] === "test" ? "Testing…" : "Test"}
                        </button>{" "}
                        <button
                          type="button"
                          className="tenant-btn-ghost"
                          disabled={!!busyById[row.id]}
                          onClick={() => void runAction(row.id, "sync")}
                        >
                          {busyById[row.id] === "sync" ? "Syncing…" : "Sync"}
                        </button>
                        <Link to={`/app/integrations/${row.id}`} className="tenant-btn-inline tenant-btn-inline--ghost">
                          Detail
                        </Link>
                      </td>
                    </tr>

                    {(runs[row.id] ?? []).slice(0, 1).map((run) => (
                      <tr key={`${row.id}-${run.id}`} className="tenant-table-subrow">
                        <td colSpan={6} style={{ background: "rgba(15, 23, 42, 0.03)" }}>
                          Last run: {run.status} · {run.records_processed} records · {run.completed_at ?? "running"}
                          {run.error_summary ? ` · ${run.error_summary}` : ""}
                        </td>
                      </tr>
                    ))}
                    </Fragment>
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
