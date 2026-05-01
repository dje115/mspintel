import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { AIProductBlockState, BackupHealthWorkspaceResponse, ServiceRiskResponse } from "../../api/types";
import { TenantAiContextNotice } from "../../components/TenantAiContextNotice";
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

type BackupAiStructured = {
  summary?: string;
  risk_themes?: Array<{ title?: string; severity?: string; detail?: string; evidence?: string }>;
  opportunity_themes?: Array<{ title?: string; detail?: string; evidence?: string }>;
  account_notes?: Array<{ customer_name?: string; note?: string }>;
  recommended_next_actions?: Array<{ owner_role?: string; action?: string; why?: string }>;
  confidence_notes?: string[];
};

function parseBackupAi(text?: string | null): BackupAiStructured | null {
  if (!text) return null;
  const trimmed = text.trim();
  if (!trimmed) return null;
  const candidates = [trimmed];
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced?.[1]) candidates.push(fenced[1].trim());
  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate) as BackupAiStructured;
      if (parsed && typeof parsed === "object") return parsed;
    } catch {
      continue;
    }
  }
  return null;
}

function severityClass(level?: string): string {
  const n = String(level || "").toLowerCase();
  if (n === "high") return "tenant-badge tenant-badge--at_risk";
  if (n === "medium") return "tenant-badge tenant-badge--watch";
  return "tenant-badge tenant-badge--muted";
}

export function ServiceRiskPage() {
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<ServiceRiskResponse | null>(null);
  const [backupHealth, setBackupHealth] = useState<BackupHealthWorkspaceResponse | null>(null);
  const [backupAi, setBackupAi] = useState<AIProductBlockState | null>(null);
  const [backupAiBusy, setBackupAiBusy] = useState(false);
  const [backupAiErr, setBackupAiErr] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadError(null);
    void (async () => {
      try {
        setData(await api.workspaceServiceRisk(accessToken, currentTenantId));
      } catch (err: unknown) {
        setLoadError(err instanceof Error ? err.message : "Unable to load service risk");
        return;
      }
      try {
        setBackupHealth(await api.backupHealthWorkspace(accessToken, currentTenantId));
      } catch {
        setBackupHealth(null);
      }
      try {
        setBackupAi(await api.getBackupHealthAiLatest(accessToken, currentTenantId));
      } catch {
        setBackupAi({ status: "not_generated", message: "No AI run yet for this context." });
      }
    })();
  }, [accessToken, currentTenantId]);

  const backupStructured = useMemo(() => parseBackupAi(backupAi?.text), [backupAi?.text]);

  const runBackupAi = async () => {
    if (!accessToken || !currentTenantId) return;
    setBackupAiBusy(true);
    setBackupAiErr(null);
    try {
      await api.postBackupHealthAiInsights(accessToken, currentTenantId);
      setBackupAi(await api.getBackupHealthAiLatest(accessToken, currentTenantId));
    } catch (e: unknown) {
      setBackupAiErr(e instanceof Error ? e.message : "AI generation failed");
    } finally {
      setBackupAiBusy(false);
    }
  };

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

  const backupConn = Number(data.backup.metrics.backup_integrations_configured ?? 0);
  const backupJobs = Number(data.backup.metrics.tracked_backup_jobs ?? 0);
  const factsTotal = Number(data.backup.metrics.tracked_protection_facts ?? 0);
  const backupBadge =
    backupConn === 0 ? (
      <span className="tenant-badge tenant-badge--muted">Awaiting integration</span>
    ) : factsTotal === 0 ? (
      <span className="tenant-badge tenant-badge--watch">Registered · run sync</span>
    ) : (
      <span className="tenant-badge tenant-badge--active">Live signals</span>
    );

  const factCountForAi = Number(backupHealth?.summary?.total_protection_facts ?? factsTotal);

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Backup &amp; service risk</h1>
        <p className="tenant-page-sub">
          Backup metrics come from registered BCDR connectors (Veeam today; additional vendors use the same fact model).
          Delivery metrics use open tickets, at-risk accounts, and lost quotes from synced PSA and commercial data.
        </p>
      </header>
      <TenantAiContextNotice compact />

      <div className="tenant-two-col">
        <section className="tenant-panel tenant-panel--accent">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">{data.backup.title}</h2>
            {backupBadge}
          </div>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.15rem" }}>
            <p className="tenant-page-sub" style={{ marginBottom: "1rem" }}>
              {data.backup.summary}
            </p>
            <MetricsList metrics={data.backup.metrics} />
            <p className="muted" style={{ marginTop: "1rem", fontSize: "0.88rem" }}>
              <Link className="tenant-panel-link" to="/app/integrations">
                Manage backup connections
              </Link>
              {" — "}run sync to ingest jobs, workloads, repositories, and restore-test rows for AI and rollups.
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

      <section className="tenant-panel" style={{ marginTop: "1.25rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Backup intelligence (AI)</h2>
          <span className="tenant-badge tenant-badge--muted">Portfolio</span>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.15rem" }}>
          <p className="tenant-page-sub" style={{ marginBottom: "0.75rem" }}>
            Synthesises ingested backup facts — for example job health, incremental change anomalies, unprotected workloads,
            repository stress, and overdue restore tests. Outputs are advisory; validate with your backup team before
            customer commitments.
          </p>
          {backupHealth?.coverage_notes?.length ? (
            <ul className="muted" style={{ fontSize: "0.85rem", marginBottom: "1rem" }}>
              {backupHealth.coverage_notes.slice(0, 3).map((n) => (
                <li key={n.slice(0, 48)}>{n}</li>
              ))}
            </ul>
          ) : null}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center", marginBottom: "1rem" }}>
            <button
              type="button"
              className="tenant-btn-inline"
              disabled={backupAiBusy || factCountForAi <= 0}
              onClick={() => void runBackupAi()}
              title={
                factCountForAi <= 0
                  ? "Run a backup connector sync first so facts exist for the model."
                  : "Generate portfolio backup risks & opportunities"
              }
            >
              {backupAiBusy ? "Generating…" : "Generate backup insights"}
            </button>
            {factCountForAi <= 0 ? (
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                No protection facts yet — connect Veeam (or another supported backup vendor) and sync.
              </span>
            ) : null}
          </div>
          {backupAiErr ? <p className="tenant-error">{backupAiErr}</p> : null}
          {backupAi && backupAi.status !== "succeeded" && backupAi.status !== "not_generated" ? (
            <p className="muted" style={{ fontSize: "0.88rem" }}>
              AI status: {backupAi.status}
              {backupAi.message ? ` — ${backupAi.message}` : ""}
            </p>
          ) : null}
          {backupStructured ? (
            <div className="tenant-rec-card" style={{ fontSize: "0.9rem" }}>
              {backupStructured.summary ? <p style={{ marginTop: 0 }}>{backupStructured.summary}</p> : null}
              {backupStructured.risk_themes?.length ? (
                <div style={{ marginTop: "0.75rem" }}>
                  <strong>Risks / gaps</strong>
                  <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.1rem" }}>
                    {backupStructured.risk_themes.map((t, i) => (
                      <li key={`${t.title ?? "r"}-${i}`}>
                        <span className={severityClass(t.severity)} style={{ marginRight: "0.35rem" }}>
                          {t.severity ?? "note"}
                        </span>
                        <strong>{t.title}</strong>
                        {t.detail ? ` — ${t.detail}` : ""}
                        {t.evidence ? <span className="muted"> ({t.evidence})</span> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {backupStructured.opportunity_themes?.length ? (
                <div style={{ marginTop: "0.75rem" }}>
                  <strong>Opportunities</strong>
                  <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.1rem" }}>
                    {backupStructured.opportunity_themes.map((t, i) => (
                      <li key={`${t.title ?? "o"}-${i}`}>
                        <strong>{t.title}</strong>
                        {t.detail ? ` — ${t.detail}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {backupStructured.account_notes?.length ? (
                <div style={{ marginTop: "0.75rem" }}>
                  <strong>Account notes</strong>
                  <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.1rem" }}>
                    {backupStructured.account_notes.map((a, i) => (
                      <li key={`${a.customer_name ?? "a"}-${i}`}>
                        <strong>{a.customer_name ?? "Account"}</strong>
                        {a.note ? `: ${a.note}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {backupStructured.recommended_next_actions?.length ? (
                <div style={{ marginTop: "0.75rem" }}>
                  <strong>Next actions</strong>
                  <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.1rem" }}>
                    {backupStructured.recommended_next_actions.map((x, i) => (
                      <li key={`${x.action ?? "x"}-${i}`}>
                        {x.owner_role ? <span className="muted">{x.owner_role}: </span> : null}
                        {x.action}
                        {x.why ? <span className="muted"> — {x.why}</span> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {backupStructured.confidence_notes?.length ? (
                <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.82rem" }}>
                  {backupStructured.confidence_notes.join(" ")}
                </p>
              ) : null}
            </div>
          ) : backupAi?.status === "succeeded" && backupAi.text ? (
            <pre className="tenant-rec-card" style={{ fontSize: "0.82rem", whiteSpace: "pre-wrap" }}>
              {backupAi.text}
            </pre>
          ) : (
            <p className="muted" style={{ fontSize: "0.88rem" }}>
              {backupJobs > 0 || factsTotal > 0
                ? "Run the generator to produce a structured risks & opportunities brief from your latest backup sync."
                : "After the first successful backup sync, you can generate portfolio-level AI insights here."}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
