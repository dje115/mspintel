import { Link } from "react-router-dom";

export function DataQualityPage() {
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
          <div className="tenant-empty">
            <p className="tenant-empty-title">Monitoring shell enabled</p>
            <p>
              Use <Link to="/app/integrations">Integrations</Link> to run tests and sync jobs now. This page will expand to
              include freshness SLAs, entity-level drift alerts, and remediation workflows.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
