import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { IntegrationCoverageResponse } from "../../api/types";
import { useSession } from "../../state/session";

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
          Visibility into connector freshness, failed syncs, and coverage gaps before they degrade recommendations.
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
            <div className="tenant-grid tenant-grid--cards-3">
              <article className="tenant-card">
                <h3 style={{ marginTop: 0 }}>Connected systems</h3>
                <p className="tenant-metric-big">{coverage.connected_systems}</p>
              </article>
              <article className="tenant-card">
                <h3 style={{ marginTop: 0 }}>Unresolved mappings</h3>
                <p className="tenant-metric-big">{coverage.unresolved_mappings}</p>
              </article>
              <article className="tenant-card">
                <h3 style={{ marginTop: 0 }}>Weak mapping signals</h3>
                <p className="tenant-metric-big">{coverage.weak_mappings}</p>
              </article>
            </div>
          ) : null}
          <p className="muted" style={{ marginTop: "1rem" }}>
            Use <Link to="/app/integrations">Integrations</Link> for lifecycle/scope controls and{" "}
            <Link to="/app/integrations/mappings">Mapping review</Link> to resolve identity conflicts safely.
          </p>
        </div>
      </section>
    </div>
  );
}
