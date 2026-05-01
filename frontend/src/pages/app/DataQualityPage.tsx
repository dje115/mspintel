import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { IntegrationCoverageResponse } from "../../api/types";
import { useSession } from "../../state/session";

function formatSystemType(t: string): string {
  return t.replace(/_/g, " ");
}

export function DataQualityPage() {
  const { accessToken, currentTenantId } = useSession();
  const [coverage, setCoverage] = useState<IntegrationCoverageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoading(true);
    setError(null);
    void api
      .integrationCoverage(accessToken, currentTenantId)
      .then(setCoverage)
      .catch((err: unknown) => {
        setCoverage(null);
        setError(err instanceof Error ? err.message : "Unable to load data quality coverage");
      })
      .finally(() => setLoading(false));
  }, [accessToken, currentTenantId]);

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Data quality & sync health</h1>
        <p className="tenant-page-sub">
          Connector registration, customer linkage, and mapping review workload — drawn from the same sources as
          Integrations and Mapping review.
        </p>
        <p style={{ marginTop: "0.5rem" }}>
          <span className="tenant-badge tenant-badge--active">Live data</span>
        </p>
      </header>
      <section className="tenant-panel">
        <div className="tenant-panel-body">
          {loading ? <p className="tenant-skeleton">Loading connector coverage…</p> : null}

          {error ? (
            <div className="tenant-empty">
              <p className="tenant-empty-title">Coverage unavailable</p>
              <p className="tenant-error">{error}</p>
            </div>
          ) : null}

          {!loading && !error && !coverage ? (
            <div className="tenant-empty">
              <p className="tenant-empty-title">No coverage data yet</p>
              <p>Connect and sync at least one source to populate quality metrics.</p>
            </div>
          ) : null}

          {coverage ? (
            <>
              <div className="tenant-grid tenant-grid--cards-3" style={{ marginBottom: "1.25rem" }}>
                <article className="tenant-card">
                  <h3 style={{ marginTop: 0 }}>Connected systems</h3>
                  <p className="tenant-metric-big">{coverage.connected_systems}</p>
                  <p className="muted" style={{ fontSize: "0.82rem", marginBottom: 0 }}>
                    Active source connections
                  </p>
                </article>
                <article className="tenant-card">
                  <h3 style={{ marginTop: 0 }}>Unresolved mappings</h3>
                  <p className="tenant-metric-big">{coverage.unresolved_mappings}</p>
                  <p className="muted" style={{ fontSize: "0.82rem", marginBottom: 0 }}>
                    Needs review or acceptance
                  </p>
                </article>
                <article className="tenant-card">
                  <h3 style={{ marginTop: 0 }}>Weak mapping signals</h3>
                  <p className="tenant-metric-big">{coverage.weak_mappings}</p>
                  <p className="muted" style={{ fontSize: "0.82rem", marginBottom: 0 }}>
                    Low-confidence suggestions
                  </p>
                </article>
              </div>
              {coverage.phased_onboarding_connections > 0 ? (
                <p className="muted" style={{ marginBottom: "1rem" }}>
                  <strong>{coverage.phased_onboarding_connections}</strong> connection(s) are in phased onboarding —
                  scope may be limited until you widen import settings.
                </p>
              ) : null}
              {coverage.items.length > 0 ? (
                <div className="tenant-table-wrap">
                  <table className="tenant-table">
                    <thead>
                      <tr>
                        <th>Connection</th>
                        <th>System</th>
                        <th>State</th>
                        <th>Import scope</th>
                        <th className="tenant-table-num">Linked customers</th>
                        <th className="tenant-table-num">Unresolved</th>
                        <th className="tenant-table-num">Weak</th>
                      </tr>
                    </thead>
                    <tbody>
                      {coverage.items.map((row) => (
                        <tr key={row.source_connection_id}>
                          <td>{row.source_connection_name}</td>
                          <td>{formatSystemType(row.system_type)}</td>
                          <td>{row.lifecycle_state.replace(/_/g, " ")}</td>
                          <td>{row.import_scope_mode.replace(/_/g, " ")}</td>
                          <td className="tenant-table-num">{row.linked_customers}</td>
                          <td className="tenant-table-num">{row.unresolved_mappings}</td>
                          <td className="tenant-table-num">{row.weak_mappings}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="tenant-empty" style={{ textAlign: "left" }}>
                  <p className="tenant-empty-title">No connections yet</p>
                  <p className="muted" style={{ marginBottom: 0 }}>
                    Add a source under Integrations — this table fills in per connection with live mapping counts.
                  </p>
                </div>
              )}
            </>
          ) : null}
          <p className="muted" style={{ marginTop: "1rem" }}>
            Use <Link to="/app/integrations">Integrations</Link> for lifecycle and sync, and{" "}
            <Link to="/app/integrations/mappings">Mapping review</Link> to resolve identities.
          </p>
        </div>
      </section>
    </div>
  );
}
