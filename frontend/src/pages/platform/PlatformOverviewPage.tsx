import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { PlatformOverview } from "../../api/types";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";

export function PlatformOverviewPage() {
  const { accessToken } = useSession();
  const [data, setData] = useState<PlatformOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    void api
      .platformOverview(accessToken)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [accessToken]);

  return (
    <div className="stack platform-page">
      <div>
        <h1>Platform overview</h1>
        <p className="muted">Cross-tenant health and entry points for administration.</p>
        <p className="version-tag">UI v{APP_VERSION} | API v{data?.app_version ?? "—"}</p>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div className="cards">
        <section className="card">
          <h2>Tenants</h2>
          <p className="platform-stat">{data?.tenant_count ?? "—"}</p>
          <Link className="platform-inline-link" to="/platform/tenants">
            Manage tenants →
          </Link>
        </section>
        <section className="card">
          <h2>Users</h2>
          <p className="platform-stat">{data?.user_count ?? "—"}</p>
          <p className="muted small-print">Global user identities across all tenants.</p>
        </section>
        <section className="card">
          <h2>Subscriptions</h2>
          <p className="platform-stat">{data?.subscription_count ?? "—"}</p>
          <p className="muted small-print">Rows in the subscriptions table (billing foundation).</p>
        </section>
        <section className="card">
          <h2>Environment</h2>
          <p className="platform-stat subtle">{data?.environment ?? "—"}</p>
          <Link className="platform-inline-link" to="/platform/system-status">
            System status →
          </Link>
        </section>
      </div>
    </div>
  );
}
