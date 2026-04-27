import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { ConnectorCatalogItem, IntegrationCoverageResponse, IntegrationSyncRun, SourceConnection } from "../../api/types";
import { useSession } from "../../state/session";

export function IntegrationsPage() {
  const { accessToken, currentTenantId } = useSession();
  const [rows, setRows] = useState<SourceConnection[]>([]);
  const [catalog, setCatalog] = useState<ConnectorCatalogItem[]>([]);
  const [runs, setRuns] = useState<Record<string, IntegrationSyncRun[]>>({});
  const [busyById, setBusyById] = useState<Record<string, string>>({});
  const [coverage, setCoverage] = useState<IntegrationCoverageResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    system_type: "autotask",
    display_name: "Primary Autotask",
    base_url: "",
    auth_mode: "api_key",
    sync_cadence_minutes: 30
  });
  const [createConfig, setCreateConfig] = useState<Record<string, string>>({});

  const selectedCatalog = useMemo(
    () => catalog.find((c) => c.system_type === createForm.system_type) ?? null,
    [catalog, createForm.system_type]
  );

  useEffect(() => {
    if (!selectedCatalog) return;
    setCreateForm((prev) => ({
      ...prev,
      auth_mode: selectedCatalog.supported_auth_modes[0] ?? "api_key",
      sync_cadence_minutes: selectedCatalog.default_cadence_minutes || prev.sync_cadence_minutes
    }));
    const cfg: Record<string, string> = {};
    selectedCatalog.config_fields.forEach((f) => {
      cfg[f.key] = "";
    });
    if (selectedCatalog.system_type === "xero" || selectedCatalog.system_type === "microsoft_365") cfg.demo_mode = "true";
    setCreateConfig(cfg);
  }, [selectedCatalog]);

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    setErr(null);
    try {
      const [connections, providerCatalog, coverageRows] = await Promise.all([
        api.integrations(accessToken, currentTenantId),
        api.integrationCatalog(accessToken, currentTenantId),
        api.integrationCoverage(accessToken, currentTenantId)
      ]);
      setRows(connections);
      setCatalog(providerCatalog);
      setCoverage(coverageRows);
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

  const updateLifecycle = async (connectionId: string, patch: { lifecycle_state?: string; is_paused?: boolean; sync_behavior?: string; is_enabled?: boolean }) => {
    if (!accessToken || !currentTenantId) return;
    await api.updateIntegrationLifecycle(accessToken, currentTenantId, connectionId, patch);
    await load();
  };

  const updateScope = async (row: SourceConnection, mode: string) => {
    if (!accessToken || !currentTenantId) return;
    const defaultFilters: Record<string, unknown> = mode === "sample_limit" ? { sample_limit: 20 } : {};
    await api.updateIntegrationImportScope(accessToken, currentTenantId, row.id, { import_scope_mode: mode, filters: defaultFilters });
    await load();
  };

  const createConnection = async () => {
    if (!accessToken || !currentTenantId) return;
    setErr(null);
    try {
      await api.createIntegrationConnection(accessToken, currentTenantId, {
        system_type: createForm.system_type,
        display_name: createForm.display_name,
        base_url: createConfig.base_url || createForm.base_url || null,
        auth_mode: createForm.auth_mode,
        sync_cadence_minutes: createForm.sync_cadence_minutes,
        is_enabled: true,
        config: createConfig
      });
      setCreateConfig((prev) =>
        Object.fromEntries(
          Object.entries(prev).map(([k, v]) => [k, k.toLowerCase().includes("secret") || k.includes("token") ? "" : v])
        )
      );
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
      {coverage ? (
        <section className="tenant-grid tenant-grid--cards-3" style={{ marginBottom: "1rem" }}>
          <article className="tenant-card">
            <h3 style={{ marginTop: 0 }}>Connected systems</h3>
            <p className="tenant-metric-big">{coverage.connected_systems}</p>
          </article>
          <article className="tenant-card">
            <h3 style={{ marginTop: 0 }}>Unresolved mappings</h3>
            <p className="tenant-metric-big">{coverage.unresolved_mappings}</p>
          </article>
          <article className="tenant-card">
            <h3 style={{ marginTop: 0 }}>Phased onboarding</h3>
            <p className="tenant-metric-big">{coverage.phased_onboarding_connections}</p>
          </article>
        </section>
      ) : null}

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
              Auth mode
              <select
                className="tenant-select"
                value={createForm.auth_mode}
                onChange={(e) => setCreateForm((v) => ({ ...v, auth_mode: e.target.value }))}
              >
                {(selectedCatalog?.supported_auth_modes ?? ["api_key"]).map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
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
          {selectedCatalog ? (
            <div className="tenant-grid tenant-grid--cards-3" style={{ marginTop: "0.75rem" }}>
              {selectedCatalog.config_fields.map((f) => (
                <label key={f.key}>
                  {f.label}
                  <input
                    className="tenant-input"
                    type={f.secret ? "password" : "text"}
                    required={f.required}
                    value={createConfig[f.key] ?? ""}
                    onChange={(e) => setCreateConfig((prev) => ({ ...prev, [f.key]: e.target.value }))}
                  />
                </label>
              ))}
            </div>
          ) : null}
          {selectedCatalog && !selectedCatalog.implemented ? (
            <p className="muted" style={{ marginTop: "0.75rem" }}>
              {selectedCatalog.display_name} is scaffolded for future phases. You can still register a placeholder connection
              to track rollout planning.
            </p>
          ) : null}
          {selectedCatalog?.ui_help_text ? <p className="muted">{selectedCatalog.ui_help_text}</p> : null}
          <div style={{ marginTop: "0.9rem" }}>
            <button type="button" className="tenant-btn-primary" onClick={() => void createConnection()}>
              Save connection
            </button>
          </div>
          {selectedCatalog ? (
            <div style={{ marginTop: "0.9rem" }}>
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
                <span className="tenant-badge tenant-badge--muted">family: {selectedCatalog.system_family}</span>
                <span className="tenant-badge tenant-badge--watch">maturity: {selectedCatalog.maturity}</span>
                <span className="tenant-badge tenant-badge--muted">
                  {selectedCatalog.implemented ? "implemented" : "stub/planned"}
                </span>
              </div>
              <p className="muted" style={{ margin: 0 }}>
                Capabilities: {selectedCatalog.supports_entities.join(", ") || "none declared"}.
              </p>
            </div>
          ) : null}
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
                    <th>Lifecycle</th>
                    <th>Scope</th>
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
                      <td><span className="tenant-badge tenant-badge--muted">{row.lifecycle_state}</span></td>
                      <td>{row.import_scope_mode}</td>
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
                        <button type="button" className="tenant-btn-ghost" onClick={() => void updateLifecycle(row.id, { is_paused: !row.is_paused, lifecycle_state: !row.is_paused ? "paused" : "active" })}>
                          {row.is_paused ? "Resume" : "Pause"}
                        </button>
                        <button type="button" className="tenant-btn-ghost" onClick={() => void updateLifecycle(row.id, { is_enabled: !row.is_enabled, lifecycle_state: row.is_enabled ? "disabled" : "active" })}>
                          {row.is_enabled ? "Disable" : "Enable"}
                        </button>
                        <button type="button" className="tenant-btn-ghost" onClick={() => void updateLifecycle(row.id, { sync_behavior: row.sync_behavior === "manual_sync_only" ? "scheduled_sync_enabled" : "manual_sync_only" })}>
                          {row.sync_behavior === "manual_sync_only" ? "Scheduled mode" : "Manual mode"}
                        </button>
                        <select className="tenant-select" value={row.import_scope_mode} onChange={(e) => void updateScope(row, e.target.value)}>
                          {(catalog.find((c) => c.system_type === row.system_type)?.import_scope_modes ?? ["all"]).map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>

                    {(runs[row.id] ?? []).slice(0, 1).map((run) => (
                      <tr key={`${row.id}-${run.id}`} className="tenant-table-subrow">
                        <td colSpan={7} style={{ background: "rgba(15, 23, 42, 0.03)" }}>
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
