import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { APP_VERSION } from "../../config/version";
import type { SystemStatus } from "../../api/types";
import { useSession } from "../../state/session";

export function SystemStatusPage() {
  const { accessToken, currentTenantId } = useSession();
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api.systemStatus(accessToken, currentTenantId).then(setStatus);
  }, [accessToken, currentTenantId]);

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">System status</h1>
        <p className="tenant-page-sub">
          Live health of APIs and dependencies for this workspace. UI v{APP_VERSION}
          {status ? ` · API v${status.version}` : ""}.
        </p>
      </header>

      {!status ? (
        <div className="tenant-skeleton">Loading status…</div>
      ) : (
        <>
          <div className="tenant-kpi-row" style={{ marginBottom: "1rem" }}>
            <article className="tenant-kpi">
              <p className="tenant-kpi-label">API</p>
              <p className="tenant-kpi-value" style={{ fontSize: "1.2rem" }}>
                {status.api}
              </p>
            </article>
            <article className="tenant-kpi">
              <p className="tenant-kpi-label">Database</p>
              <p className="tenant-kpi-value" style={{ fontSize: "1.2rem" }}>
                {status.db}
              </p>
            </article>
            <article className="tenant-kpi">
              <p className="tenant-kpi-label">Redis</p>
              <p className="tenant-kpi-value" style={{ fontSize: "1.2rem" }}>
                {status.redis}
              </p>
            </article>
            <article className="tenant-kpi">
              <p className="tenant-kpi-label">Environment</p>
              <p className="tenant-kpi-value" style={{ fontSize: "1.2rem" }}>
                {status.environment}
              </p>
            </article>
          </div>
          <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Raw payload</h2>
            </div>
            <div className="tenant-panel-body" style={{ padding: "1rem" }}>
              <pre
                style={{
                  margin: 0,
                  fontSize: "0.78rem",
                  overflow: "auto",
                  background: "#f8fafc",
                  borderRadius: "8px",
                  padding: "0.75rem"
                }}
              >
                {JSON.stringify(status, null, 2)}
              </pre>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
