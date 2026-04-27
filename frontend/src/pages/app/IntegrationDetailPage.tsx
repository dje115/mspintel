import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import type { IntegrationSyncRun, SourceConnection } from "../../api/types";
import { useSession } from "../../state/session";

export function IntegrationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { accessToken, currentTenantId } = useSession();
  const [connection, setConnection] = useState<SourceConnection | null>(null);
  const [runs, setRuns] = useState<IntegrationSyncRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId || !id) return;
    void Promise.all([api.integrations(accessToken, currentTenantId), api.integrationRuns(accessToken, currentTenantId, id, 20)])
      .then(([rows, runRows]) => {
        setConnection(rows.find((r) => r.id === id) ?? null);
        setRuns(runRows);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Unable to load integration detail"));
  }, [accessToken, currentTenantId, id]);

  if (!id) return null;
  if (error) return <p className="tenant-error">{error}</p>;
  if (!connection) return <div className="tenant-skeleton">Loading integration detail…</div>;

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">{connection.display_name}</h1>
        <p className="tenant-page-sub">
          {connection.system_type} connector · {connection.lifecycle_state} · {connection.health_status} · cadence every {connection.sync_cadence_minutes} min
        </p>
      </header>
      <section className="tenant-grid tenant-grid--cards-3">
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>Connection</h3>
          <p className="muted">Base URL: {connection.base_url ?? "—"}</p>
          <p className="muted">Auth mode: {connection.auth_mode}</p>
          <p className="muted">Connector: {connection.connector_version}</p>
          <p className="muted">Import scope: {connection.import_scope_mode}</p>
          <p className="muted">Sync behavior: {connection.sync_behavior}</p>
          <Link to="/app/integrations" className="tenant-btn-inline tenant-btn-inline--ghost">
            Back to integrations
          </Link>
          <Link to="/app/integrations/mappings" className="tenant-btn-inline tenant-btn-inline--ghost">
            Mapping review queue
          </Link>
        </article>
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>Cadence</h3>
          <p className="muted">Mode: {connection.sync_mode}</p>
          <p className="muted">Last test: {connection.last_tested_at ?? "Never"}</p>
          <p className="muted">Last successful sync: {connection.last_successful_sync_at ?? "Never"}</p>
        </article>
        <article className="tenant-card">
          <h3 style={{ marginTop: 0 }}>Entities</h3>
          <p className="muted">
            {(Array.isArray(connection.connection_metadata?.supports_entities)
              ? (connection.connection_metadata?.supports_entities as string[])
              : []
            ).join(", ") || "None advertised"}
          </p>
        </article>
      </section>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Recent sync runs</h2>
        </div>
        <div className="tenant-panel-body">
          {runs.length === 0 ? (
            <p className="muted">No runs recorded yet.</p>
          ) : (
            <div className="tenant-table-wrap">
              <table className="tenant-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Trigger</th>
                    <th>Records</th>
                    <th>Started</th>
                    <th>Completed</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id}>
                      <td>{r.status}</td>
                      <td>{r.trigger_mode}</td>
                      <td>{r.records_processed}</td>
                      <td>{r.started_at ?? "—"}</td>
                      <td>{r.completed_at ?? "—"}</td>
                      <td>{r.error_summary ?? "—"}</td>
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
