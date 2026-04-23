import { useEffect, useState } from "react";

import { api } from "../../api/client";
import type { PlatformTenantList, PlatformTenantRow } from "../../api/types";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";

export function PlatformTenantsPage() {
  const { accessToken } = useSession();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PlatformTenantList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    void api
      .platformTenants(accessToken, { page, page_size: 20 })
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [accessToken, page]);

  return (
    <div className="stack platform-page">
      <div>
        <h1>Tenants</h1>
        <p className="muted">Workspaces on the platform (read-only list in this release).</p>
        <p className="version-tag">v{APP_VERSION}</p>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div className="table-wrap">
        <table className="platform-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Slug</th>
              <th>Active</th>
              <th>Onboarding</th>
              <th>Subscription</th>
              <th>Plan</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((row: PlatformTenantRow) => (
              <tr key={row.tenant_id}>
                <td>{row.name}</td>
                <td className="cell-clip" title={row.slug}>
                  {row.slug}
                </td>
                <td>{row.is_active ? "yes" : "no"}</td>
                <td>
                  {row.onboarding_status ?? "—"}
                  {row.onboarding_step ? ` / ${row.onboarding_step}` : ""}
                </td>
                <td>{row.subscription_status ?? "—"}</td>
                <td>{row.plan_name ?? row.plan_code ?? "—"}</td>
                <td>{row.created_at ? new Date(row.created_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data ? (
        <div className="pagination">
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
            Previous
          </button>
          <span className="muted">
            Page {data.page} · {data.total} total
          </span>
          <button
            type="button"
            disabled={page * data.page_size >= data.total}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      ) : null}
    </div>
  );
}
