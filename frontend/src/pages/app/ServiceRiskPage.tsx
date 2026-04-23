import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { ServiceRiskResponse } from "../../api/types";
import { useSession } from "../../state/session";

function MetricsList({ metrics }: { metrics: Record<string, number | string> }) {
  return (
    <dl className="tenant-metric-dl">
      {Object.entries(metrics).map(([k, v]) => (
        <div key={k} className="tenant-metric-dl-row">
          <dt>{k.replace(/_/g, " ")}</dt>
          <dd>{typeof v === "number" ? v : String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ServiceRiskPage() {
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<ServiceRiskResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadError(null);
    void api
      .workspaceServiceRisk(accessToken, currentTenantId)
      .then(setData)
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Unable to load service risk");
      });
  }, [accessToken, currentTenantId]);

  if (loadError) {
    return (
      <div className="tenant-page-head">
        <h1 className="tenant-page-title">Backup &amp; service risk</h1>
        <p className="tenant-error">{loadError}</p>
      </div>
    );
  }

  if (!data) {
    return <div className="tenant-skeleton">Loading risk overview…</div>;
  }

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Backup &amp; service risk</h1>
        <p className="tenant-page-sub">
          Operational view of backup health and service delivery pressure. Backup integrations will populate the first
          section; delivery metrics already reflect tickets and account risk from live data.
        </p>
      </header>

      <div className="tenant-two-col">
        <section className="tenant-panel tenant-panel--accent">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">{data.backup.title}</h2>
            {data.backup.placeholder ? (
              <span className="tenant-badge tenant-badge--watch">Preview</span>
            ) : (
              <span className="tenant-badge tenant-badge--active">Live</span>
            )}
          </div>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.15rem" }}>
            <p className="tenant-page-sub" style={{ marginBottom: "1rem" }}>
              {data.backup.summary}
            </p>
            <MetricsList metrics={data.backup.metrics} />
            <p className="muted" style={{ marginTop: "1rem", fontSize: "0.88rem" }}>
              When Veeam / Acronis / other backup connectors sync job history, this section will list failed jobs,
              stale agents, and coverage gaps by account with drill-through to customer 360.
            </p>
          </div>
        </section>

        <section className="tenant-panel">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">{data.service_delivery.title}</h2>
            <span className="tenant-badge tenant-badge--active">Live</span>
          </div>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.15rem" }}>
            <p className="tenant-page-sub" style={{ marginBottom: "1rem" }}>
              {data.service_delivery.summary}
            </p>
            <MetricsList metrics={data.service_delivery.metrics} />
            <p style={{ marginTop: "1rem", fontSize: "0.88rem" }}>
              <Link className="tenant-panel-link" to="/app/at-risk">
                Open at-risk accounts
              </Link>
              {" · "}
              <Link className="tenant-panel-link" to="/app/attention">
                Needs attention
              </Link>
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
