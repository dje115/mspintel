import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { BillingIntegrityWorkspaceResponse } from "../../api/types";
import { useSession } from "../../state/session";
import { TenantAiContextNotice } from "../../components/TenantAiContextNotice";

const formatMoney = (cents: number | null | undefined) => {
  if (!cents) return "GBP 0";
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 0
  }).format(cents / 100);
};

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
  const noXero = !summary.xero_configured;
  const noInvoices = summary.total_invoice_count === 0;
  const noMappings = summary.finance_linked_count === 0 && summary.unlinked_finance_contact_count > 0;

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Billing integrity &amp; revenue assurance</h1>
        <p className="tenant-page-sub">
          Connector-sourced finance signals for account housekeeping and revenue assurance. Conclusions stay conservative when
          service/contract context is incomplete.
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

      {noXero ? (
        <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
          <div className="tenant-panel-body">
            <p className="tenant-empty-title">Xero not configured</p>
            <p className="muted">Add a Xero connector in Integrations, then run sync to populate finance contacts and invoices.</p>
            <Link className="tenant-btn-inline" to="/app/integrations">
              Open integrations
            </Link>
          </div>
        </section>
      ) : null}

      {summary.xero_configured && noInvoices ? (
        <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
          <div className="tenant-panel-body">
            <p className="tenant-empty-title">Xero configured but no invoices synced yet</p>
            <p className="muted">
              Last sync status: {summary.xero_last_sync_status ?? "not run"}. Trigger Xero sync and review mappings.
            </p>
          </div>
        </section>
      ) : null}

      {noMappings ? (
        <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
          <div className="tenant-panel-body">
            <p className="tenant-empty-title">Finance data is present but customer linkage is incomplete</p>
            <p className="muted">
              Resolve Xero mapping rows so finance contacts link to canonical customers and customer-level insights can render.
            </p>
            <Link className="tenant-btn-inline" to="/app/integrations/mappings">
              Open mapping review
            </Link>
          </div>
        </section>
      ) : null}

      <div className="tenant-metric-grid" aria-label="Portfolio billing summary">
        <article className="tenant-metric-card">
          <h3>Accounts</h3>
          <p className="tenant-metric-big">{summary.customer_count}</p>
          <p className="tenant-metric-note">Customers in workspace.</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Finance linked</h3>
          <p className="tenant-metric-big">{summary.finance_linked_count}</p>
          <p className="tenant-metric-note">
            {summary.missing_finance_link_count} missing canonical billing link · {summary.unlinked_finance_contact_count} unlinked
            finance contacts.
          </p>
        </article>
        <article className="tenant-metric-card">
          <h3>Total invoices</h3>
          <p className="tenant-metric-big">{summary.total_invoice_count}</p>
          <p className="tenant-metric-note">Connector-sourced Xero invoice rows.</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Unpaid / overdue</h3>
          <p className="tenant-metric-big">
            {summary.unpaid_invoice_count} / {summary.overdue_invoice_count}
          </p>
          <p className="tenant-metric-note">Payment friction signals (account housekeeping context).</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Amount due</h3>
          <p className="tenant-metric-big">{formatMoney(summary.total_amount_due_cents)}</p>
          <p className="tenant-metric-note">Total outstanding across synced finance accounts.</p>
        </article>
        <article className="tenant-metric-card">
          <h3>Last Xero sync</h3>
          <p className="tenant-metric-big">{summary.xero_last_sync_status ?? "—"}</p>
          <p className="tenant-metric-note">{summary.xero_last_sync_completed_at ?? "No completed run yet"}</p>
        </article>
      </div>

      {summary.top_customer_due.length > 0 ? (
        <section className="tenant-panel" style={{ marginTop: "1rem" }}>
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Top customers by amount due</h2>
          </div>
          <div className="tenant-panel-body">
            <ul className="tenant-list-plain">
              {summary.top_customer_due.map((row) => {
                const r = row as {
                  customer_id?: string;
                  customer_name?: string;
                  amount_due_cents?: number;
                  overdue_invoice_count?: number;
                };
                return (
                  <li key={`${r.customer_id}-${r.customer_name}`} className="tenant-rec-card">
                    <Link to={`/app/customers/${r.customer_id}`}>{r.customer_name ?? "Customer"}</Link>
                    <span className="muted">
                      {" "}
                      · due {formatMoney(r.amount_due_cents ?? 0)} · overdue {r.overdue_invoice_count ?? 0}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>
      ) : null}

      <section className="tenant-panel" style={{ marginTop: "1.25rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Per-account signals</h2>
          <Link className="tenant-panel-link" to="/app/integrations/mappings">
            Mapping review
          </Link>
        </div>
        <div className="tenant-panel-body" style={{ padding: 0 }}>
          <div className="tenant-table-wrap">
            <table className="tenant-table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Finance</th>
                  <th>Unpaid / overdue</th>
                  <th>Amount due</th>
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
                    <td>
                      {a.finance_linked ? (
                        <span className="tenant-badge tenant-badge--active">Linked</span>
                      ) : (
                        <span className="tenant-badge tenant-badge--muted">Missing</span>
                      )}
                    </td>
                    <td>
                      {a.unpaid_invoice_count} / {a.overdue_invoice_count}
                    </td>
                    <td>{formatMoney(a.total_amount_due_cents)}</td>
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
