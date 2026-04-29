import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { AIProductBlockState, M365WorkspaceResponse } from "../../api/types";
import { useSession } from "../../state/session";
import { TenantAiContextNotice } from "../../components/TenantAiContextNotice";

type AiFinding = { title: string; severity?: string; detail?: string; evidence?: string };
type AiOutlier = { customer_name: string; finding?: string; detail?: string; angle?: string; talking_point?: string };
type AiAction = { owner_role?: string; action?: string; why?: string; next_action?: string };
type AiOpportunity = { title: string; service_area?: string; detail?: string; evidence?: string; next_action?: string };
type StructuredAiPayload = {
  summary?: string;
  key_findings?: AiFinding[];
  customer_outliers?: AiOutlier[];
  risks_gaps?: string[];
  opportunities?: AiOpportunity[];
  customer_conversation_angles?: AiOutlier[];
  recommended_next_actions?: AiAction[];
  confidence_notes?: string[];
  delivery_risks_or_dependencies?: string[];
};

type M365Tab = "summary" | "ai" | "customers" | "findings" | "confidence";

function parseStructuredAi(text?: string | null): StructuredAiPayload | null {
  if (!text) return null;
  const trimmed = text.trim();
  if (!trimmed) return null;
  const candidates = [trimmed];
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced?.[1]) candidates.push(fenced[1].trim());
  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate) as StructuredAiPayload;
      if (parsed && typeof parsed === "object") return parsed;
    } catch {
      continue;
    }
  }
  return null;
}

function severityBadgeClass(level?: string): string {
  const normalized = String(level || "").toLowerCase();
  if (normalized === "high") return "tenant-badge tenant-badge--warn";
  if (normalized === "medium") return "tenant-badge tenant-badge--watch";
  return "tenant-badge";
}

export function M365HealthPage() {
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<M365WorkspaceResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [aiSummary, setAiSummary] = useState<AIProductBlockState | null>(null);
  const [aiOpportunity, setAiOpportunity] = useState<AIProductBlockState | null>(null);
  const [aiBusy, setAiBusy] = useState<"" | "summary" | "opportunity">("");
  const [aiErr, setAiErr] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<M365Tab>("summary");

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setErr(null);
    void Promise.all([
      api.m365HealthWorkspace(accessToken, currentTenantId),
      api.getM365HealthAiSummary(accessToken, currentTenantId).catch(() => ({ status: "not_generated" } as AIProductBlockState)),
      api.getM365HealthAiOpportunity(accessToken, currentTenantId).catch(
        () => ({ status: "not_generated" } as AIProductBlockState)
      ),
    ])
      .then(([workspace, summary, opportunity]) => {
        setData(workspace);
        setAiSummary(summary);
        setAiOpportunity(opportunity);
      })
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : "Failed to load Microsoft 365 health"));
  }, [accessToken, currentTenantId]);

  const refreshAiState = async () => {
    if (!accessToken || !currentTenantId) return;
    const [summary, opportunity] = await Promise.all([
      api.getM365HealthAiSummary(accessToken, currentTenantId),
      api.getM365HealthAiOpportunity(accessToken, currentTenantId),
    ]);
    setAiSummary(summary);
    setAiOpportunity(opportunity);
  };

  const runAi = async (kind: "summary" | "opportunity") => {
    if (!accessToken || !currentTenantId) return;
    setAiErr(null);
    setAiBusy(kind);
    try {
      if (kind === "summary") {
        await api.postM365HealthAiSummary(accessToken, currentTenantId);
      } else {
        await api.postM365HealthAiOpportunity(accessToken, currentTenantId);
      }
      await refreshAiState();
    } catch (e: unknown) {
      setAiErr(e instanceof Error ? e.message : "AI generation failed");
    } finally {
      setAiBusy("");
    }
  };

  const linkedCount = data?.summary.linked_count ?? 0;
  const noM365Data = linkedCount === 0;
  const noProviderConfigured =
    aiSummary?.status === "unavailable" &&
    (aiSummary.message || "").toLowerCase().includes("configure a default ai provider");
  const summaryStructured = useMemo(() => parseStructuredAi(aiSummary?.text), [aiSummary?.text]);
  const opportunityStructured = useMemo(() => parseStructuredAi(aiOpportunity?.text), [aiOpportunity?.text]);
  const findingsCount = useMemo(
    () => data?.customers.reduce((acc, row) => acc + (row.hygiene_findings?.length || 0) + (row.optimisation_findings?.length || 0), 0) ?? 0,
    [data?.customers]
  );
  const highConfidenceCount = useMemo(
    () => data?.customers.filter((row) => row.confidence_level === "high").length ?? 0,
    [data?.customers]
  );
  const mediumConfidenceCount = useMemo(
    () => data?.customers.filter((row) => row.confidence_level === "medium").length ?? 0,
    [data?.customers]
  );

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Microsoft 365 health</h1>
        <p className="tenant-page-sub">
          Thin v1 posture view for M365 hygiene, identity activity, mailbox footprint, and licence optimisation signals.
        </p>
      </header>
      <TenantAiContextNotice compact />
      {err ? <p className="tenant-error">{err}</p> : null}
      {!data ? (
        <div className="tenant-skeleton">Loading Microsoft posture…</div>
      ) : (
        <>
          {!data.summary.connector_configured ? (
            <section className="tenant-card" style={{ marginBottom: "1rem" }}>
              <div className="tenant-panel-head">
                <h3 style={{ margin: 0 }}>Needs connector setup</h3>
                <span className="tenant-badge tenant-badge--warn">Needs connector setup</span>
              </div>
              <p className="muted" style={{ marginTop: "0.5rem" }}>
                No Microsoft 365 connection is configured for this tenant yet.
              </p>
              <Link to="/app/integrations" className="tenant-btn-inline tenant-btn-inline--ghost">
                Open integrations
              </Link>
            </section>
          ) : null}
          {data.summary.connector_configured && data.summary.linked_count < data.summary.customer_count ? (
            <section className="tenant-card" style={{ marginBottom: "1rem" }}>
              <div className="tenant-panel-head">
                <h3 style={{ margin: 0 }}>Partially connected</h3>
                <span className="tenant-badge tenant-badge--watch">Partially connected</span>
              </div>
              <p className="muted" style={{ marginTop: "0.5rem" }}>
                Only {data.summary.linked_count} of {data.summary.customer_count} customers have canonical M365 posture rows.
              </p>
            </section>
          ) : null}
          <div className="tenant-segmented">
            {[
              { key: "summary", label: "Summary" },
              { key: "ai", label: "AI insights" },
              { key: "customers", label: "Customers", count: data.customers.length },
              { key: "findings", label: "Findings", count: findingsCount },
              { key: "confidence", label: "Data confidence" },
            ].map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`tenant-segment ${activeTab === tab.key ? "is-active" : ""}`}
                onClick={() => setActiveTab(tab.key as M365Tab)}
              >
                {tab.label}
                {typeof tab.count === "number" ? <span className="tenant-segment-count">{tab.count}</span> : null}
              </button>
            ))}
          </div>

          {activeTab === "summary" ? <section className="tenant-metric-grid">
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
          </section> : null}

          {activeTab === "summary" ? <section className="tenant-grid tenant-grid--cards-3" style={{ marginTop: "1rem" }}>
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
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Last sync</h3>
              <p className="muted">Status: {data.summary.last_sync_status ?? "not_run"}</p>
              <p className="muted">
                Completed:{" "}
                {data.summary.last_sync_completed_at
                  ? new Date(data.summary.last_sync_completed_at).toLocaleString()
                  : "Not yet"}
              </p>
            </article>
          </section> : null}

          {activeTab === "ai" ? <section className="tenant-panel tenant-panel--m365-ai" style={{ marginBottom: "1rem" }}>
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">AI M365 insights</h2>
              <span className="tenant-badge tenant-badge--watch">Portfolio scope</span>
            </div>
            <div className="tenant-panel-body">
              <p className="muted" style={{ marginTop: 0 }}>
                AI uses scoped portfolio context plus tenant MSP profile. It does not run automatically and records lineage per task run.
              </p>
              {aiErr ? <p className="tenant-error">{aiErr}</p> : null}
              {noM365Data ? (
                <p className="muted">
                  No linked Microsoft 365 posture rows yet. Run sync and complete mapping/import before generating AI insights.
                </p>
              ) : null}
              {noProviderConfigured ? (
                <p className="muted">
                  No runnable AI provider is configured. Check <Link to="/app/ai-settings">AI settings</Link> and test the provider.
                </p>
              ) : null}
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
                <button
                  type="button"
                  className="tenant-btn"
                  disabled={aiBusy !== "" || noM365Data}
                  onClick={() => void runAi("summary")}
                >
                  {aiSummary?.status === "succeeded" ? "Refresh AI hygiene summary" : "Generate AI hygiene summary"}
                </button>
                <button
                  type="button"
                  className="tenant-btn-ghost"
                  disabled={aiBusy !== "" || noM365Data}
                  onClick={() => void runAi("opportunity")}
                >
                  {aiOpportunity?.status === "succeeded"
                    ? "Refresh AI opportunity guidance"
                    : "Generate AI opportunity guidance"}
                </button>
              </div>
              <div className="tenant-grid tenant-grid--cards-2">
                <article className="tenant-card tenant-card--m365-ai">
                  <h3 style={{ marginTop: 0 }}>Hygiene summary</h3>
                  <p className="muted" style={{ marginTop: 0 }}>
                    Status: {aiSummary?.status ?? "not_generated"}
                    {aiSummary?.model_used ? ` · ${aiSummary.model_used}` : ""}
                    {aiSummary?.last_completed_at
                      ? ` · ${new Date(aiSummary.last_completed_at).toLocaleString()}`
                      : ""}
                  </p>
                  <p className="tenant-m365-ai-summary">
                    {summaryStructured?.summary || aiSummary?.message || "Not generated yet. Use the button above."}
                  </p>
                  {summaryStructured?.key_findings?.length ? (
                    <div className="tenant-m365-ai-list">
                      {summaryStructured.key_findings.slice(0, 4).map((finding) => (
                        <div key={finding.title} className="tenant-m365-ai-list-item">
                          <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem", flexWrap: "wrap" }}>
                            <strong>{finding.title}</strong>
                            <span className={severityBadgeClass(finding.severity)}>{finding.severity ?? "info"}</span>
                          </div>
                          {finding.detail ? <p className="muted">{finding.detail}</p> : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="tenant-m365-ai-fallback">
                      {aiSummary?.text || aiSummary?.message || "No structured output yet."}
                    </p>
                  )}
                </article>
                <article className="tenant-card tenant-card--m365-ai">
                  <h3 style={{ marginTop: 0 }}>Opportunity guidance</h3>
                  <p className="muted" style={{ marginTop: 0 }}>
                    Status: {aiOpportunity?.status ?? "not_generated"}
                    {aiOpportunity?.model_used ? ` · ${aiOpportunity.model_used}` : ""}
                    {aiOpportunity?.last_completed_at
                      ? ` · ${new Date(aiOpportunity.last_completed_at).toLocaleString()}`
                      : ""}
                  </p>
                  <p className="tenant-m365-ai-summary">
                    {opportunityStructured?.summary || aiOpportunity?.message || "Not generated yet. Use the button above."}
                  </p>
                  {opportunityStructured?.opportunities?.length ? (
                    <div className="tenant-m365-ai-list">
                      {opportunityStructured.opportunities.slice(0, 4).map((op) => (
                        <div key={op.title} className="tenant-m365-ai-list-item">
                          <strong>{op.title}</strong>
                          {op.detail ? <p className="muted">{op.detail}</p> : null}
                          {op.evidence ? <p className="muted">Evidence: {op.evidence}</p> : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="tenant-m365-ai-fallback">
                      {aiOpportunity?.text || aiOpportunity?.message || "No structured output yet."}
                    </p>
                  )}
                </article>
              </div>
            </div>
          </section> : null}

          {activeTab === "customers" ? <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Customer posture rows</h2>
              <span className="tenant-badge">Portfolio totals shown separately</span>
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
          </section> : null}

          {activeTab === "findings" ? <section className="tenant-grid tenant-grid--cards-2" style={{ marginTop: "1rem" }}>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Portfolio findings</h3>
              <ul className="tenant-list-plain">
                {data.coverage_notes.map((n) => (
                  <li key={n} className="tenant-rec-card muted">
                    {n}
                  </li>
                ))}
              </ul>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Top customer outliers</h3>
              <ul className="tenant-list-plain">
                {data.customers
                  .slice()
                  .sort(
                    (a, b) =>
                      (b.inactive_users_30d ?? 0) +
                      (b.unused_licences ?? 0) +
                      (b.shared_mailbox_count ?? 0) -
                      ((a.inactive_users_30d ?? 0) + (a.unused_licences ?? 0) + (a.shared_mailbox_count ?? 0))
                  )
                  .slice(0, 8)
                  .map((row) => (
                    <li key={row.customer_id} className="tenant-rec-card">
                      <strong>{row.customer_name}</strong>
                      <span className="muted">
                        inactive: {row.inactive_users_30d ?? 0} · unused licences: {row.unused_licences ?? 0} · shared mailboxes:{" "}
                        {row.shared_mailbox_count ?? 0}
                      </span>
                    </li>
                  ))}
              </ul>
            </article>
          </section> : null}

          {activeTab === "confidence" ? <section className="tenant-grid tenant-grid--cards-3" style={{ marginTop: "1rem" }}>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Confidence distribution</h3>
              <p className="muted">
                High: {highConfidenceCount} · Medium: {mediumConfidenceCount} · Low:{" "}
                {Math.max((data.customers?.length ?? 0) - highConfidenceCount - mediumConfidenceCount, 0)}
              </p>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Connector and sync status</h3>
              <p className="muted">Health: {data.summary.connector_health_status}</p>
              <p className="muted">Lifecycle: {data.summary.connector_lifecycle_state}</p>
              <p className="muted">Last sync: {data.summary.last_sync_status ?? "not_run"}</p>
            </article>
            <article className="tenant-card">
              <h3 style={{ marginTop: 0 }}>Data confidence notes</h3>
              <ul className="tenant-list-plain">
                {data.coverage_notes.map((n) => (
                  <li key={n} className="tenant-rec-card muted">
                    {n}
                  </li>
                ))}
              </ul>
            </article>
          </section> : null}
        </>
      )}
    </div>
  );
}

