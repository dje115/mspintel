import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { BillingIntegrityWorkspaceResponse } from "../../api/types";
import { useSession } from "../../state/session";
import { TenantAiContextNotice } from "../../components/TenantAiContextNotice";

export function BillingIntegrityPage() {
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<BillingIntegrityWorkspaceResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setErr(null);
    void api
      .billingIntegrityWorkspace(accessToken, currentTenantId)
      .then(setData)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : "Unable to load billing integrity"));
  }, [accessToken, currentTenantId]);

  if (err) {
    return <p className="tenant-error">{err}</p>;
  }
  if (!data) {
    return <div className="tenant-skeleton">Loading billing integrity workspace…</div>;
  }

  const { summary } = data;

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Billing integrity &amp; revenue assurance</h1>
        <p className="tenant-page-sub">
          Canonical finance snapshots vs service footprint heuristics. This is <strong>not</strong> a full accounting
          view — signals are only as strong as connector coverage and synced fields.
        </p>
      </header>
      <TenantAiContextNotice compact />

      <section className="tenant-panel tenant-panel--accent" style={{ marginBottom: "1.25rem" }}>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
          <p style={{ margin: 0, fontWeight: 600 }}>Coverage &amp; honesty</p>
          <ul className="tenant-ai-placeholder-list" style={{ marginTop: "0.5rem", color: "#475569" }}>
            {data.coverage_notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      </section>

      <div className="tenant-metric-grid" aria-label="Portfolio billing summary">
        <article className="tenant-metric-card">
          <h3>Accounts</h3>
          <p className="tenant-metric-big">{summary.customer_count}</p>
          <p className="tenant-metric-note">Customers in workspace.</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Finance linked</h3>
          <p className="tenant-metric-big">{summary.finance_linked_count}</p>
          <p className="tenant-metric-note">{summary.missing_finance_link_count} missing canonical billing link.</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Underbilling candidates</h3>
          <p className="tenant-metric-big">{summary.underbilling_candidate_count}</p>
          <p className="tenant-metric-note">Service mailboxes &gt; billed seats (+1) on latest snapshot.</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Overbilling risk</h3>
          <p className="tenant-metric-big">{summary.overbilling_risk_count}</p>
          <p className="tenant-metric-note">Billed mailboxes materially above measured actives — verify SKUs.</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Payment friction</h3>
          <p className="tenant-metric-big">{summary.payment_friction_count}</p>
          <p className="tenant-metric-note">Non-trivial invoice friction flags on snapshots.</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Orphan billing rows</h3>
          <p className="tenant-metric-big">{summary.orphan_billing_account_count}</p>
          <p className="tenant-metric-note">Billing accounts without a customer link (needs cleanup).</p>
        </article>
      </div>

      <section className="tenant-panel" style={{ marginTop: "1.25rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Per-account signals</h2>
          <Link className="tenant-panel-link" to="/app/integrations">
            Integrations
          </Link>
        </div>
        <div className="tenant-panel-body" style={{ padding: 0 }}>
          <div className="tenant-table-wrap">
            <table className="tenant-table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Finance</th>
                  <th>Billed MB</th>
                  <th>Service MB</th>
                  <th>Payment</th>
                  <th>Confidence</th>
                  <th>Signals</th>
                </tr>
              </thead>
              <tbody>
                {data.accounts.map((a) => (
                  <tr key={a.customer_id}>
                    <td>
                      <Link to={`/app/customers/${a.customer_id}`}>{a.customer_name}</Link>
                    </td>
                    <td>{a.finance_linked ? <span className="tenant-badge tenant-badge--active">Linked</span> : <span className="tenant-badge tenant-badge--muted">Missing</span>}</td>
                    <td>{a.billed_mailboxes ?? "—"}</td>
                    <td>{a.service_mailboxes ?? "—"}</td>
                    <td className="muted">{a.payment_friction ?? "—"}</td>
                    <td className="muted">{a.confidence_level ?? "—"}</td>
                    <td style={{ maxWidth: "22rem", fontSize: "0.82rem" }}>
                      {a.signals.length ? (
                        <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
                          {a.signals.map((s) => (
                            <li key={s}>{s}</li>
                          ))}
                        </ul>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
