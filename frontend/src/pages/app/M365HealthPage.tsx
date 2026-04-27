import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { M365WorkspaceResponse } from "../../api/types";
import { useSession } from "../../state/session";

export function M365HealthPage() {
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<M365WorkspaceResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setErr(null);
    void api
      .m365HealthWorkspace(accessToken, currentTenantId)
      .then(setData)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : "Failed to load Microsoft 365 health"));
  }, [accessToken, currentTenantId]);

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Microsoft 365 health</h1>
        <p className="tenant-page-sub">
          Thin v1 posture view for M365 hygiene, identity activity, mailbox footprint, and licence optimisation signals.
        </p>
      </header>
      {err ? <p className="tenant-error">{err}</p> : null}
      {!data ? (
        <div className="tenant-skeleton">Loading Microsoft posture…</div>
      ) : (
        <>
          <section className="tenant-metric-grid">
            <article className="tenant-metric-card">
              <h3>Linked accounts</h3>
              <p className="tenant-metric-big">{data.summary.linked_count}</p>
              <p className="tenant-metric-note">Customers with canonical M365 posture rows.</p>
            </article>
            <article className="tenant-metric-card">
              <h3>Licensed / active</h3>
              <p className="tenant-metric-big">
                {data.summary.licensed_users_total} / {data.summary.active_users_total}
              </p>
              <p className="tenant-metric-note">Directional portfolio-level M365 identity usage.</p>
            </article>
            <article className="tenant-metric-card">
              <h3>Inactive users</h3>
              <p className="tenant-metric-big">{data.summary.inactive_users_total}</p>
              <p className="tenant-metric-note">Potential lifecycle/optimisation conversation queue.</p>
            </article>
            <article className="tenant-metric-card">
              <h3>Stale / disabled</h3>
              <p className="tenant-metric-big">
                {data.summary.stale_users_total} / {data.summary.disabled_users_total}
              </p>
              <p className="tenant-metric-note">Identity hygiene indicators (directional).</p>
            </article>
            <article className="tenant-metric-card">
              <h3>Mailboxes / shared</h3>
              <p className="tenant-metric-big">
                {data.summary.mailbox_total} / {data.summary.shared_mailbox_total}
              </p>
              <p className="tenant-metric-note">Shared mailbox sprawl is directional, not an audit-grade count.</p>
            </article>
          </section>

          <section className="tenant-grid tenant-grid--cards-3" style={{ marginTop: "1rem" }}>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Licensing</h3>
              <p className="muted">Licensed users: {data.summary.licensed_users_total}</p>
              <p className="muted">Unused/stale identities should drive true-up and cleanup discussions.</p>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Billing impact</h3>
              <p className="muted">Mismatch candidates: {data.summary.billing_mismatch_candidate_count}</p>
              <Link to="/app/billing-integrity" className="tenant-btn-inline tenant-btn-inline--ghost">
                Open billing integrity
              </Link>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Opportunities</h3>
              <p className="muted">Optimisation candidates: {data.summary.optimisation_candidate_count}</p>
              <p className="muted">Use Review/QBR prep to turn hygiene findings into customer actions.</p>
            </article>
          </section>

          <section className="tenant-panel" style={{ marginTop: "1rem" }}>
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Portfolio findings</h2>
              <span className="tenant-badge tenant-badge--watch">
                Optimisation candidates: {data.summary.optimisation_candidate_count}
              </span>
            </div>
            <div className="tenant-panel-body">
              <ul className="tenant-list-plain">
                {data.coverage_notes.map((n) => (
                  <li key={n} className="tenant-rec-card muted">
                    {n}
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Customer posture rows</h2>
            </div>
            <div className="tenant-panel-body">
              <div className="tenant-table-wrap">
                <table className="tenant-table">
                  <thead>
                    <tr>
                      <th>Customer</th>
                      <th>Licensed / active / inactive</th>
                      <th>Mailboxes</th>
                      <th>Unused licences</th>
                      <th>Stale / disabled</th>
                      <th>MFA %</th>
                      <th>Signals</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.customers.map((r) => (
                      <tr key={r.customer_id}>
                        <td>
                          <Link className="tenant-btn-inline" to={`/app/customers/${r.customer_id}`}>
                            {r.customer_name}
                          </Link>
                          <div className="muted" style={{ fontSize: "0.8rem" }}>
                            confidence: {r.confidence_level}
                          </div>
                        </td>
                        <td>
                          {r.licensed_users ?? "—"} / {r.active_users_30d ?? "—"} / {r.inactive_users_30d ?? "—"}
                        </td>
                        <td>
                          {r.mailbox_count ?? "—"} (shared {r.shared_mailbox_count ?? "—"})
                        </td>
                        <td>{r.unused_licences ?? "—"}</td>
                        <td>
                          {r.stale_users_90d ?? "—"} / {r.disabled_users ?? "—"}
                        </td>
                        <td>{r.mfa_coverage_pct ?? "—"}</td>
                        <td>
                          {[...(r.billing_impact_signals || []), ...(r.hygiene_findings || []), ...(r.optimisation_findings || [])]
                            .slice(0, 2)
                            .join(" · ") || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

