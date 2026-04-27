import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { IntegrationCoverageResponse } from "../../api/types";
import { useSession } from "../../state/session";

export function DataQualityPage() {
  const { accessToken, currentTenantId } = useSession();
  const [coverage, setCoverage] = useState<IntegrationCoverageResponse | null>(null);
  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api.integrationCoverage(accessToken, currentTenantId).then(setCoverage).catch(() => undefined);
  }, [accessToken, currentTenantId]);

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Data quality & sync health</h1>
        <p className="tenant-page-sub">
          Visibility into connector freshness, failed syncs, and coverage gaps before they degrade recommendations.
        </p>
      </header>
      <section className="tenant-panel">
        <div className="tenant-panel-body">
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
