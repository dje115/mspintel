import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import type {
  CustomerDetailResponse,
  CustomerListItem,
  CustomerReviewArtifactOut,
  CustomerReviewLatestArtifactsResponse,
  ReviewAiGenerationResponse,
  ReviewWorkspaceContextResponse
} from "../../api/types";
import { AccountManagerGuidanceShell } from "../../components/AccountManagerGuidanceShell";
import { TenantAiContextNotice } from "../../components/TenantAiContextNotice";
import { useSession } from "../../state/session";
import {
  accountManagerArtifactToCards,
  buildCommercialReviewSlice,
  mergeWarningLists,
  needsCustomerReviewFromArtifact,
  scanTextForReviewWarnings,
  stripMarkdownFences
} from "../../utils/reviewDisplayUtils";
const REVIEW_TABS = [
  { id: "overview", label: "Prep overview" },
  { id: "agenda", label: "AI agenda" },
  { id: "account", label: "Account manager" },
  { id: "email", label: "Customer email" },
  { id: "report", label: "Customer report" },
  { id: "history", label: "AI history" },
  { id: "confidence", label: "Data confidence" }
] as const;

type ReviewTabId = (typeof REVIEW_TABS)[number]["id"];

function FinanceReviewStrip({ detail }: { detail: CustomerDetailResponse }) {
  const fin = detail.finance;
  if (!fin) return null;
  return (
    <section className="tenant-panel tenant-review-no-print" style={{ marginBottom: "1rem" }}>
      <div className="tenant-panel-head">
        <h2 className="tenant-panel-title">Finance &amp; billing (QBR context)</h2>
        <Link className="tenant-panel-link" to="/app/billing-integrity">
          Billing integrity workspace
        </Link>
      </div>
      <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
        {fin.finance_linked ? (
          <>
            <p className="muted" style={{ marginTop: 0, fontSize: "0.88rem" }}>
              Canonical snapshot {fin.snapshot_effective_date ?? "—"} · confidence{" "}
              <strong>{fin.confidence_level ?? "—"}</strong>
            </p>
            <p className="muted" style={{ fontSize: "0.88rem" }}>
              Billed vs service mailboxes: <strong>{fin.billed_mailboxes ?? "—"}</strong> vs{" "}
              <strong>{fin.service_active_mailboxes ?? "—"}</strong> · payment friction{" "}
              <strong>{fin.payment_status_summary ?? "—"}</strong>
            </p>
            {fin.integrity_highlights.length > 0 ? (
              <ul className="tenant-list-plain" style={{ marginBottom: 0 }}>
                {fin.integrity_highlights.map((h) => (
                  <li key={h} className="tenant-rec-card">
                    {h}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted" style={{ marginBottom: 0 }}>
                No mismatch flags on the latest snapshot — still reconcile with finance before commitments.
              </p>
            )}
          </>
        ) : (
          <p className="muted" style={{ marginTop: 0, marginBottom: 0, fontSize: "0.88rem" }}>
            No canonical finance linkage for this account. Keep commercial discussion qualitative until accounting data is
            connected.
          </p>
        )}
      </div>
    </section>
  );
}

function lostQuotesCount(quotes: CustomerDetailResponse["quotes"]) {
  return quotes.filter((q) => (q.status ?? "").toLowerCase() === "lost").length;
}

function CommercialReviewCards({
  detail,
  className
}: {
  detail: CustomerDetailResponse;
  className?: string;
}) {
  const slice = buildCommercialReviewSlice(detail);
  return (
    <section className={className ?? "tenant-review-commerce"} aria-label="Commercial pipeline">
      <div className="tenant-review-commerce-grid">
        <article className="tenant-review-commerce-card">
          <h3 className="tenant-review-commerce-title">Open opportunities</h3>
          {slice.openOpportunities.length === 0 ? (
            <p className="muted tenant-review-commerce-empty">
              {slice.hasCommercialRows ? "No open pipeline rows on file." : slice.emptyNote}
            </p>
          ) : (
            <ul className="tenant-review-commerce-list">
              {slice.openOpportunities.map((o) => (
                <li key={o.id}>
                  <strong>{o.title}</strong>
                  <span className="muted"> · {o.status}</span>
                  {o.value_cents != null ? <span className="muted"> · value on file</span> : null}
                  {o.suggested_next_action ? (
                    <p className="tenant-review-commerce-angle">{o.suggested_next_action}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="tenant-review-commerce-card">
          <h3 className="tenant-review-commerce-title">Stalled / revisit</h3>
          {slice.stalledOpportunities.length === 0 ? (
            <p className="muted tenant-review-commerce-empty">
              {slice.hasCommercialRows ? "No stalled or revisit-flagged opportunities." : "—"}
            </p>
          ) : (
            <ul className="tenant-review-commerce-list">
              {slice.stalledOpportunities.map((o) => (
                <li key={o.id}>
                  <strong>{o.title}</strong>
                  <span className="muted"> · {o.status}</span>
                  {o.revisit_reason ? <p className="tenant-review-commerce-angle">{o.revisit_reason}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="tenant-review-commerce-card">
          <h3 className="tenant-review-commerce-title">Lost quotes</h3>
          {slice.lostQuotes.length === 0 ? (
            <p className="muted tenant-review-commerce-empty">
              {slice.hasCommercialRows ? "No lost quotes on file for this account." : "—"}
            </p>
          ) : (
            <ul className="tenant-review-commerce-list">
              {slice.lostQuotes.map((q) => (
                <li key={q.id}>
                  <strong>{q.title}</strong>
                  {q.suggested_next_action ? (
                    <p className="tenant-review-commerce-angle">{q.suggested_next_action}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="tenant-review-commerce-card tenant-review-commerce-card--angle">
          <h3 className="tenant-review-commerce-title">Discussion angle</h3>
          {slice.discussionAngle ? (
            <p className="tenant-review-commerce-angle">{slice.discussionAngle}</p>
          ) : (
            <p className="muted tenant-review-commerce-empty">
              {slice.hasCommercialRows ? "No suggested next action text on commercial rows." : slice.emptyNote}
            </p>
          )}
        </article>
      </div>
    </section>
  );
}

function AccountManagerStructuredBlock({
  label,
  artifact,
  genWarnings
}: {
  label: string;
  artifact: CustomerReviewArtifactOut | null;
  genWarnings?: string[] | null;
}) {
  const { cards, placeholderWarnings } = accountManagerArtifactToCards(artifact);
  const merged = mergeWarningLists(genWarnings, placeholderWarnings);
  const showPh = merged.some((w) => /placeholder|fenced|\[[^\]]+\]/i.test(w));
  return (
    <div className="tenant-review-am-block">
      <h3 className="tenant-review-subhead">{label}</h3>
      {merged.length ? <WarningsList warnings={merged} /> : null}
      {showPh ? (
        <p className="tenant-review-ph-note" role="status">
          Draft may contain template tokens or fenced blocks — use as rehearsal notes, not customer-ready copy.
        </p>
      ) : null}
      {!artifact?.full_output_text && !artifact?.full_output_json ? (
        <p className="muted">No saved output yet — generate to persist meeting prep for this account.</p>
      ) : cards.length ? (
        <div className="tenant-review-am-grid">
          {cards.map((c) => (
            <article key={c.id} className="tenant-review-am-card">
              <h4 className="tenant-review-am-card-title">{c.title}</h4>
              {c.bullets.length ? (
                <ul className="tenant-review-am-card-list">
                  {c.bullets.map((b, bi) => (
                    <li key={`${c.id}-${bi}`}>{b}</li>
                  ))}
                </ul>
              ) : (
                <p className="tenant-review-am-card-body">{c.body}</p>
              )}
            </article>
          ))}
        </div>
      ) : (
        <p className="muted">Unable to structure this output — check AI history for raw text.</p>
      )}
    </div>
  );
}

function strList(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

function M365UserBars({ detail }: { detail: CustomerDetailResponse }) {
  const m = detail.m365;
  if (!m?.linked) return <p className="muted">M365 not linked — chart unavailable.</p>;
  const active = Number(m.active_users_30d ?? 0);
  const inactive = Number(m.inactive_users_30d ?? 0);
  const total = Math.max(1, active + inactive);
  const ap = Math.round((active / total) * 100);
  const ip = 100 - ap;
  return (
    <div className="tenant-review-chart">
      <p className="tenant-review-chart-title">Licensed users — activity (30d)</p>
      <div className="tenant-review-chart-bar">
        <span className="tenant-review-chart-seg tenant-review-chart-seg--active" style={{ width: `${ap}%` }} />
        <span className="tenant-review-chart-seg tenant-review-chart-seg--inactive" style={{ width: `${ip}%` }} />
      </div>
      <p className="tenant-review-chart-legend muted">
        Active <strong>{m.active_users_30d ?? "—"}</strong> · Inactive <strong>{m.inactive_users_30d ?? "—"}</strong>
      </p>
    </div>
  );
}

function AiMetaRow({ label, outcome }: { label: string; outcome: ReviewAiGenerationResponse | null }) {
  if (!outcome?.completed_at) return null;
  return (
    <p className="tenant-review-ai-meta muted">
      {label}: {outcome.model_used ?? outcome.provider_family ?? "—"} · {new Date(outcome.completed_at).toLocaleString()}
    </p>
  );
}

function AiOutcomeBanner({ outcome }: { outcome: ReviewAiGenerationResponse | null }) {
  if (!outcome?.status || outcome.status === "succeeded") return null;
  const msg =
    outcome.message ||
    (outcome.status === "skipped"
      ? "This AI task is disabled for your tenant — enable it under AI engines or set a default provider."
      : `Generation status: ${outcome.status}`);
  return (
    <div className="tenant-review-ai-outcome" role="status">
      <strong>AI run did not complete successfully.</strong> <span className="muted">{msg}</span>
    </div>
  );
}

function WarningsList({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return (
    <ul className="tenant-review-warn-list">
      {warnings.map((w) => (
        <li key={w}>{w}</li>
      ))}
    </ul>
  );
}

function AgendaCards({ artifact }: { artifact: CustomerReviewArtifactOut | null }) {
  const o = artifact?.full_output_json;
  if (!o) {
    return <p className="muted">No stored agenda yet. Generate one — outputs are saved for this account.</p>;
  }
  const title = typeof o.meeting_title === "string" ? o.meeting_title : artifact?.title ?? "Review agenda";
  const objectives = strList(o.objectives);
  const sections = Array.isArray(o.agenda_sections) ? o.agenda_sections : [];
  return (
    <div className="tenant-review-structured">
      <h3 className="tenant-review-structured-title">{title}</h3>
      {objectives.length > 0 ? (
        <section>
          <h4>Objectives</h4>
          <ul>
            {objectives.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {sections.map((sec, i) => {
        const s = sec as Record<string, unknown>;
        const st = typeof s.title === "string" ? s.title : `Section ${i + 1}`;
        const dm = typeof s.duration_minutes === "number" ? s.duration_minutes : null;
        const tp = strList(s.talking_points);
        return (
          <section key={st + String(i)} className="tenant-review-agenda-section">
            <h4>
              {st}
              {dm != null ? <span className="muted"> · {dm} min</span> : null}
            </h4>
            {tp.length ? (
              <ul>
                {tp.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            ) : null}
          </section>
        );
      })}
      {strList(o.suggested_questions).length ? (
        <section>
          <h4>Questions</h4>
          <ul>
            {strList(o.suggested_questions).map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {strList(o.follow_up_actions).length ? (
        <section>
          <h4>Follow-up actions</h4>
          <ul>
            {strList(o.follow_up_actions).map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {strList(o.confidence_notes).length ? (
        <section>
          <h4>Confidence notes</h4>
          <ul className="muted">
            {strList(o.confidence_notes).map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function EmailPanel({
  artifact,
  liveWarnings
}: {
  artifact: CustomerReviewArtifactOut | null;
  liveWarnings?: string[] | null;
}) {
  const o = artifact?.full_output_json;
  const subjectRaw = o && typeof o.subject === "string" ? o.subject : "";
  const bodyRaw = o && typeof o.body === "string" ? o.body : artifact?.full_output_text ?? "";
  const subject = stripMarkdownFences(subjectRaw);
  const body = stripMarkdownFences(bodyRaw);
  const needs = needsCustomerReviewFromArtifact(artifact);
  const scanWarns = scanTextForReviewWarnings(`${subject}\n${body}`);
  const mergedWarns = mergeWarningLists(liveWarnings, artifact?.output_warnings, scanWarns);
  const copy = async (t: string) => {
    try {
      await navigator.clipboard.writeText(t);
    } catch {
      /* ignore */
    }
  };
  return (
    <div>
      <p className="tenant-review-disclaimer">
        Draft only — review before sending. MSPIntel does not send email from this screen.
      </p>
      {needs || mergedWarns.length ? (
        <div className="tenant-review-needs-review" role="status">
          <strong>Needs review</strong>
          <span className="muted"> — output may include placeholders or unsafe patterns. Do not send as final customer copy until cleaned.</span>
        </div>
      ) : null}
      <WarningsList warnings={mergedWarns} />
      <label className="tenant-review-field-label">Subject</label>
      <div className="tenant-review-copy-row tenant-review-no-print">
        <input className="tenant-review-input" readOnly value={subject} aria-label="Email subject" />
        <button type="button" className="tenant-btn-inline" onClick={() => void copy(subject)}>
          Copy subject
        </button>
      </div>
      <label className="tenant-review-field-label">Body</label>
      <textarea className="tenant-review-textarea" readOnly rows={14} value={body} aria-label="Email body" />
      <div className="tenant-review-actions tenant-review-no-print">
        <button type="button" className="tenant-btn-inline" onClick={() => void copy(body)}>
          Copy body
        </button>
        <button type="button" className="tenant-btn-inline" onClick={() => void copy(`Subject: ${subject}\n\n${body}`)}>
          Copy full
        </button>
      </div>
    </div>
  );
}

function ReportDocument({
  detail,
  artifact,
  liveWarnings
}: {
  detail: CustomerDetailResponse;
  artifact: CustomerReviewArtifactOut | null;
  liveWarnings?: string[] | null;
}) {
  const o = artifact?.full_output_json;
  const title = (o && typeof o.title === "string" ? o.title : null) ?? `${detail.name} — review brief`;
  const exec = o && typeof o.executive_summary === "string" ? o.executive_summary : "";
  const needs = needsCustomerReviewFromArtifact(artifact);
  const scanBlob = [
    exec,
    ...strList(o?.recommendations),
    ...strList(o?.next_steps),
    ...strList(o?.data_notes),
    ...strList(o?.confidence_notes)
  ].join("\n");
  const mergedWarns = mergeWarningLists(liveWarnings, artifact?.output_warnings, scanTextForReviewWarnings(scanBlob));
  const pairs = (key: string) => {
    const arr = o && Array.isArray(o[key]) ? (o[key] as Record<string, unknown>[]) : [];
    return arr.map((row, i) => (
      <div key={i} className="tenant-review-report-card">
        <strong>{String(row.label ?? "")}</strong>
        <p>{String(row.detail ?? "")}</p>
      </div>
    ));
  };
  return (
    <div id="review-customer-report-root" className="tenant-review-report-doc">
      <header className="tenant-review-report-header">
        <p className="tenant-review-report-brand">MSPIntel</p>
        <h1>{title}</h1>
        <p className="muted">
          {detail.name} · Prepared {new Date().toLocaleDateString()}
        </p>
        {needs || mergedWarns.length ? (
          <div className="tenant-review-needs-review tenant-review-report-banner" role="status">
            <strong>Needs review</strong>
            <span className="muted"> — placeholders or formatting issues may be present. Validate before sharing externally.</span>
          </div>
        ) : null}
        <WarningsList warnings={mergedWarns} />
      </header>
      {exec ? (
        <section className="tenant-review-report-block">
          <h2>Executive summary</h2>
          <p>{exec}</p>
        </section>
      ) : null}
      <section className="tenant-review-report-block">{pairs("highlights")}</section>
      <section className="tenant-review-report-block">
        <h2>Service snapshot</h2>
        {pairs("service_snapshot")}
      </section>
      <section className="tenant-review-report-block">
        <h2>Microsoft 365</h2>
        {pairs("m365_snapshot")}
      </section>
      <section className="tenant-review-report-block">
        <h2>Risks &amp; actions</h2>
        {pairs("risks_and_actions")}
      </section>
      {strList(o?.recommendations).length ? (
        <section className="tenant-review-report-block">
          <h2>Recommendations</h2>
          <ul>
            {strList(o?.recommendations).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {strList(o?.next_steps).length ? (
        <section className="tenant-review-report-block">
          <h2>Next steps</h2>
          <ul>
            {strList(o?.next_steps).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <section className="tenant-review-report-block tenant-review-report-commerce-wrap">
        <h2>Commercial snapshot</h2>
        <CommercialReviewCards detail={detail} className="tenant-review-commerce tenant-review-commerce--embedded" />
      </section>
      <section className="tenant-review-report-block muted">
        <h2>Data &amp; confidence</h2>
        {strList(o?.data_notes).map((n) => (
          <p key={n}>{n}</p>
        ))}
        {strList(o?.confidence_notes).map((n) => (
          <p key={n}>{n}</p>
        ))}
      </section>
      <footer className="tenant-review-report-footer">Prepared with MSPIntel — connector-sourced context; validate before commitments.</footer>
    </div>
  );
}

export function ReviewsPage() {
  const { accessToken, currentTenantId } = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const customerId = searchParams.get("customer_id") ?? "";
  const tabParam = (searchParams.get("tab") ?? "overview") as ReviewTabId;
  const view = searchParams.get("view") ?? "";
  const tab: ReviewTabId = REVIEW_TABS.some((t) => t.id === tabParam) ? tabParam : "overview";

  const [customerOptions, setCustomerOptions] = useState<CustomerListItem[]>([]);
  const [detail, setDetail] = useState<CustomerDetailResponse | null>(null);
  const [loadListError, setLoadListError] = useState<string | null>(null);
  const [loadDetailError, setLoadDetailError] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<ReviewWorkspaceContextResponse | null>(null);
  const [latest, setLatest] = useState<CustomerReviewLatestArtifactsResponse | null>(null);
  const [history, setHistory] = useState<CustomerReviewArtifactOut[]>([]);
  const [historyType, setHistoryType] = useState<string>("");
  const [reviewLoadError, setReviewLoadError] = useState<string | null>(null);
  const [genBusy, setGenBusy] = useState<string | null>(null);
  const [lastGen, setLastGen] = useState<Record<string, ReviewAiGenerationResponse | null>>({});
  const [emailTone, setEmailTone] = useState<string>("professional");

  const setTab = (id: ReviewTabId) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", id);
    if (view === "report" && id !== "report") next.delete("view");
    setSearchParams(next, { replace: true });
  };

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadListError(null);
    void api
      .customers(accessToken, currentTenantId, { page: 1, page_size: 100 })
      .then((r) => setCustomerOptions(r.items))
      .catch((e: unknown) => setLoadListError(e instanceof Error ? e.message : "Unable to load accounts"));
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    if (!accessToken || !currentTenantId || !customerId) {
      setDetail(null);
      setLoadDetailError(null);
      setWorkspace(null);
      setLatest(null);
      setHistory([]);
      return;
    }
    setLoadDetailError(null);
    void api
      .customerDetail(accessToken, currentTenantId, customerId)
      .then(setDetail)
      .catch((e: unknown) => {
        setDetail(null);
        setLoadDetailError(e instanceof Error ? e.message : "Unable to load account");
      });
  }, [accessToken, currentTenantId, customerId]);

  const refreshReviewPack = useCallback(async () => {
    if (!accessToken || !currentTenantId || !customerId) return;
    setReviewLoadError(null);
    try {
      const [ctx, lat, hist] = await Promise.all([
        api.reviewWorkspaceContext(accessToken, currentTenantId, customerId),
        api.reviewArtifactsLatest(accessToken, currentTenantId, customerId),
        api.reviewArtifactsList(accessToken, currentTenantId, customerId, {
          artifact_type: historyType || undefined,
          limit: 80
        })
      ]);
      setWorkspace(ctx);
      setLatest(lat);
      setHistory(hist.items);
    } catch (e: unknown) {
      setReviewLoadError(e instanceof Error ? e.message : "Unable to load review workspace");
    }
  }, [accessToken, currentTenantId, customerId, historyType]);

  useEffect(() => {
    void refreshReviewPack();
  }, [refreshReviewPack]);

  const whatToCover = useMemo(() => {
    if (!detail) return [];
    const lines: string[] = [];
    if (detail.recommendation_summary.length) {
      lines.push(...detail.recommendation_summary.slice(0, 4));
    }
    if (detail.open_tickets_count > 0) {
      lines.push(`Service pressure: ${detail.open_tickets_count} open ticket(s) — review SLA and recurring themes.`);
    }
    if (detail.open_opportunities_count > 0) {
      lines.push(`${detail.open_opportunities_count} open opportunit(y/ies) — align roadmap and next commercial step.`);
    }
    const lost = lostQuotesCount(detail.quotes);
    if (lost > 0) {
      lines.push(`${lost} lost quote(s) — decide whether to revisit with a win-back angle.`);
    }
    const fin = detail.finance;
    const risk = detail.risk_engine;
    if (risk) {
      lines.push(
        `Risk engine watch-outs: ${risk.risk_level} risk / ${risk.attention_level} attention (${risk.confidence_level} confidence).`
      );
      risk.reason_codes.slice(0, 2).forEach((r) => lines.push(`Risk factor: ${r}`));
    }
    if (fin?.finance_linked) {
      lines.push(
        `Billing alignment: canonical finance linked (confidence ${fin.confidence_level ?? "unknown"}) — review billed vs service mailboxes before the meeting.`
      );
      fin.integrity_highlights.slice(0, 2).forEach((h) => lines.push(`Billing signal: ${h}`));
    } else if (fin) {
      lines.push("Billing alignment: no canonical finance linkage yet — treat commercial numbers as incomplete.");
    }
    if (detail.m365?.linked) {
      lines.push(
        `Microsoft 365 hygiene: ${detail.m365.active_users_30d ?? "—"} active users, ${detail.m365.inactive_users_30d ?? "—"} inactive, ${detail.m365.unused_licences ?? "—"} unused licences.`
      );
      lines.push(
        `Identity lifecycle: ${detail.m365.stale_users_90d ?? "—"} stale users (90d), ${detail.m365.disabled_users ?? "—"} disabled identities.`
      );
      detail.m365.hygiene_findings.slice(0, 1).forEach((h) => lines.push(`M365 hygiene note: ${h}`));
      detail.m365.optimisation_findings.slice(0, 1).forEach((h) => lines.push(`M365 optimisation note: ${h}`));
      detail.m365.billing_impact_signals.slice(0, 1).forEach((h) => lines.push(`M365 billing impact: ${h}`));
    } else if (detail.m365) {
      lines.push("Microsoft 365 hygiene view is not linked — keep technical posture statements conservative.");
    }
    if (lines.length === 0) {
      lines.push("Light-touch account: confirm value narrative, roadmap, and any latent expansion signals.");
    }
    return lines;
  }, [detail]);

  const dataGaps = useMemo(() => {
    if (!detail) return [];
    const gaps: string[] = [];
    if (!detail.owner_name) gaps.push("No account owner assigned — assign for clearer accountability.");
    if (detail.open_tickets_count === 0 && detail.recommendations.length === 0) {
      gaps.push("Limited operational signals in-app — deepen PSA sync for ticket and recommendation coverage.");
    }
    if (!detail.latest_scores) gaps.push("Score snapshot missing — scoring engine may still be warming for this tenant.");
    if (!detail.finance?.finance_linked) {
      gaps.push("Canonical finance not linked — QBR commercial narrative should stay high-level until accounting sync improves.");
    } else if ((detail.finance.confidence_level ?? "").toLowerCase().includes("low")) {
      gaps.push("Finance confidence is low on-file — validate figures with finance before committing to targets.");
    }
    if (!detail.risk_engine) {
      gaps.push("Risk Engine snapshot missing — run risk recompute before finalising review priorities.");
    } else if ((detail.risk_engine.confidence_level ?? "").toLowerCase().includes("low")) {
      gaps.push("Risk confidence is low — treat watch-outs as heuristic until coverage improves.");
    }
    if (!detail.m365?.linked) {
      gaps.push("M365 connector not linked — hygiene/licence optimisation points may be incomplete.");
    }
    gaps.push("Microsoft 365, backup telemetry, telephony, and deeper accounting reads will strengthen confidence over time.");
    return gaps;
  }, [detail]);

  const onSelectCustomer = (id: string) => {
    if (!id) {
      const next = new URLSearchParams(searchParams);
      next.delete("customer_id");
      next.delete("tab");
      next.delete("view");
      setSearchParams(next, { replace: true });
      return;
    }
    navigate(`/app/reviews?customer_id=${encodeURIComponent(id)}&tab=overview`, { replace: true });
  };

  const runGen = async (key: string, fn: () => Promise<ReviewAiGenerationResponse>) => {
    if (!accessToken || !currentTenantId || !customerId) return;
    setGenBusy(key);
    setLastGen((s) => ({ ...s, [key]: null }));
    try {
      const out = await fn();
      setLastGen((s) => ({ ...s, [key]: out }));
      await refreshReviewPack();
    } catch (e: unknown) {
      setLastGen((s) => ({
        ...s,
        [key]: {
          run_id: "",
          status: "failed",
          task_type: key,
          message: e instanceof Error ? e.message : "Generation failed"
        } as ReviewAiGenerationResponse
      }));
    } finally {
      setGenBusy(null);
    }
  };

  const latestAgenda = latest?.by_type?.review_agenda ?? null;
  const latestEmail = latest?.by_type?.customer_email_draft ?? null;
  const latestReport = latest?.by_type?.customer_report ?? null;
  const latestNotes = latest?.by_type?.account_manager_notes ?? null;
  const latestScript = latest?.by_type?.call_script ?? null;

  const rw = workspace?.review_workspace as Record<string, unknown> | undefined;
  const cov = (rw?.connector_coverage ?? detail?.connector_coverage) as Record<string, unknown> | undefined;

  return (
    <div className={`tenant-review-page ${view === "report" ? "tenant-review-page--print-mode" : ""}`}>
      <header className="tenant-page-head tenant-review-no-print">
        <h1 className="tenant-page-title">Review &amp; QBR workspace</h1>
        <p className="tenant-page-sub">
          AI-assisted meeting pack for customer reviews — connector-backed context, explicit generate actions, and saved
          outputs per account. Nothing sends automatically.
        </p>
      </header>
      <TenantAiContextNotice compact />

      {!detail && (
        <section className="tenant-panel tenant-panel--accent tenant-review-no-print" style={{ marginBottom: "1.25rem" }}>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
            <p style={{ margin: 0, fontWeight: 600, color: "#0f172a" }}>What this workspace gives you</p>
            <ul className="tenant-ai-placeholder-list" style={{ color: "#475569", marginTop: "0.5rem" }}>
              <li>Executive prep overview with coverage and readiness signals</li>
              <li>Structured AI agenda, account-manager prep, customer email draft, and printable report</li>
              <li>History of prior generations with compact summaries fed into the next run</li>
            </ul>
          </div>
        </section>
      )}

      <div className="tenant-review-toolbar tenant-review-no-print">
        <div style={{ flex: "1 1 220px" }}>
          <label htmlFor="review-customer-select">Account</label>
          <select
            id="review-customer-select"
            className="tenant-review-select"
            value={customerId}
            onChange={(e) => onSelectCustomer(e.target.value)}
          >
            <option value="">Select an account…</option>
            {customerOptions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
                {c.status === "at_risk" ? " · at risk" : c.status === "watch" ? " · watch" : ""}
              </option>
            ))}
          </select>
          {loadListError ? <p className="tenant-error" style={{ marginTop: "0.35rem" }}>{loadListError}</p> : null}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
          <Link to="/app/customers" className="tenant-btn-inline tenant-btn-inline--ghost">
            Browse accounts
          </Link>
          <Link to="/app/mappings" className="tenant-btn-inline tenant-btn-inline--ghost">
            Mappings &amp; import
          </Link>
          {customerId ? (
            <Link to={`/app/customers/${customerId}`} className="tenant-btn-inline">
              Customer 360
            </Link>
          ) : null}
        </div>
      </div>

      {loadDetailError ? <p className="tenant-error">{loadDetailError}</p> : null}
      {reviewLoadError ? <p className="tenant-error">{reviewLoadError}</p> : null}

      {customerId && !detail && !loadDetailError ? <div className="tenant-skeleton">Loading account…</div> : null}

      {!customerId && (
        <>
          <section className="tenant-panel tenant-review-no-print">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Quick picks</h2>
              <Link className="tenant-panel-link" to="/app/at-risk">
                At-risk workspace
              </Link>
            </div>
            <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
              {customerOptions.length === 0 ? (
                <div className="tenant-empty">
                  <p className="tenant-empty-title">No accounts yet</p>
                  <p>
                    Run structural seed, start Connector Lab, sync M365, then import customers from mappings — or sync your
                    PSA.
                  </p>
                </div>
              ) : (
                <div className="tenant-grid tenant-grid--cards-3">
                  {customerOptions.slice(0, 6).map((c) => (
                    <article key={c.id} className="tenant-card tenant-review-card-pick">
                      <h3 style={{ marginTop: 0 }}>{c.name}</h3>
                      <p className="tenant-page-sub muted">
                        Risk {c.risk_score ?? "—"} · Attention {c.attention_score ?? "—"}
                      </p>
                      <button type="button" className="tenant-btn-inline" onClick={() => onSelectCustomer(c.id)}>
                        Open review workspace
                      </button>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </section>
          <AccountManagerGuidanceShell contextLine="Select an account to attach guidance to a specific customer context." compact />
        </>
      )}

      {customerId && detail ? (
        <>
          <nav className="tenant-review-tabs tenant-review-no-print" aria-label="Review workspace sections">
            {REVIEW_TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`tenant-review-tab ${tab === t.id ? "tenant-review-tab--active" : ""}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>

          {tab === "overview" ? (
            <>
              <FinanceReviewStrip detail={detail} />
              <CommercialReviewCards detail={detail} />
              <div className="tenant-review-kpi-row tenant-review-no-print" aria-label="Account health">
                <div className="tenant-review-kpi tenant-review-kpi--risk">
                  <p className="tenant-review-kpi-label">Risk</p>
                  <p className="tenant-review-kpi-value">{detail.latest_scores?.risk_score ?? "—"}</p>
                </div>
                <div className="tenant-review-kpi tenant-review-kpi--attention">
                  <p className="tenant-review-kpi-label">Attention</p>
                  <p className="tenant-review-kpi-value">{detail.latest_scores?.attention_score ?? "—"}</p>
                </div>
                <div className="tenant-review-kpi">
                  <p className="tenant-review-kpi-label">Growth</p>
                  <p className="tenant-review-kpi-value">{detail.latest_scores?.growth_score ?? "—"}</p>
                </div>
                <div className="tenant-review-kpi">
                  <p className="tenant-review-kpi-label">Open tickets</p>
                  <p className="tenant-review-kpi-value">{detail.open_tickets_count}</p>
                </div>
                <div className="tenant-review-kpi">
                  <p className="tenant-review-kpi-label">Open recs</p>
                  <p className="tenant-review-kpi-value">{detail.recommendations.filter((r) => r.status === "open").length}</p>
                </div>
                <div className="tenant-review-kpi">
                  <p className="tenant-review-kpi-label">Lost quotes</p>
                  <p className="tenant-review-kpi-value">{lostQuotesCount(detail.quotes)}</p>
                </div>
              </div>

              <div className="tenant-two-col tenant-review-no-print">
                <section className="tenant-panel tenant-review-panel-accent">
                  <div className="tenant-panel-head">
                    <h2 className="tenant-panel-title">Source coverage</h2>
                  </div>
                  <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                    <p className="muted" style={{ marginTop: 0 }}>
                      {typeof cov?.confidence_note === "string" ? cov.confidence_note : "Mapping and connector coverage for this account."}
                    </p>
                    <div className="tenant-review-chip-row">
                      <span className={`tenant-review-chip ${detail.m365?.linked ? "tenant-review-chip--ok" : "tenant-review-chip--warn"}`}>
                        M365 {detail.m365?.linked ? "linked" : "not linked"}
                      </span>
                      <span className={`tenant-review-chip ${detail.finance?.finance_linked ? "tenant-review-chip--ok" : "tenant-review-chip--warn"}`}>
                        Finance {detail.finance?.finance_linked ? "linked" : "not linked"}
                      </span>
                      <span className={`tenant-review-chip ${(cov?.connected_systems as string[] | undefined)?.length ? "tenant-review-chip--ok" : "tenant-review-chip--muted"}`}>
                        PSA mappings: {(cov?.connected_systems as string[] | undefined)?.join(", ") || "—"}
                      </span>
                    </div>
                    {typeof cov?.unresolved_mapping_count === "number" && cov.unresolved_mapping_count > 0 ? (
                      <p className="tenant-review-pill-warn">
                        {String(cov.unresolved_mapping_count)} unresolved mapping(s) — visit{" "}
                        <Link to="/app/mappings">Mappings</Link>.
                      </p>
                    ) : null}
                    <p className="muted" style={{ fontSize: "0.82rem", marginBottom: 0 }}>
                      Context hash: {workspace?.source_data_version ?? "—"}
                    </p>
                  </div>
                </section>
                <section className="tenant-panel">
                  <div className="tenant-panel-head">
                    <h2 className="tenant-panel-title">Saved AI outputs</h2>
                  </div>
                  <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                    <ul className="tenant-review-latest-list">
                      <li>
                        Agenda: {latestAgenda?.created_at ? new Date(latestAgenda.created_at).toLocaleString() : "—"}
                      </li>
                      <li>
                        Email draft: {latestEmail?.created_at ? new Date(latestEmail.created_at).toLocaleString() : "—"}
                      </li>
                      <li>
                        Report: {latestReport?.created_at ? new Date(latestReport.created_at).toLocaleString() : "—"}
                      </li>
                    </ul>
                  </div>
                </section>
              </div>

              <div className="tenant-two-col tenant-review-no-print">
                <section className="tenant-panel">
                  <div className="tenant-panel-head">
                    <h2 className="tenant-panel-title">Discussion priorities</h2>
                  </div>
                  <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                    <ul className="tenant-list-plain">
                      {whatToCover.map((line) => (
                        <li key={line} className="tenant-rec-card">
                          {line}
                        </li>
                      ))}
                    </ul>
                  </div>
                </section>
                <section className="tenant-panel">
                  <div className="tenant-panel-head">
                    <h2 className="tenant-panel-title">M365 snapshot</h2>
                  </div>
                  <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                    <M365UserBars detail={detail} />
                  </div>
                </section>
              </div>

              <AccountManagerGuidanceShell customerId={detail.id} contextLine={`Account: ${detail.name}`} />
            </>
          ) : null}

          {tab === "agenda" ? (
            <section className="tenant-panel tenant-review-ai-panel">
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">AI review agenda</h2>
                <button
                  type="button"
                  className="tenant-btn-inline"
                  disabled={!!genBusy || !accessToken}
                  onClick={() =>
                    accessToken &&
                    currentTenantId &&
                    void runGen("agenda", () => api.postReviewAgendaAi(accessToken, currentTenantId, customerId))
                  }
                >
                  {genBusy === "agenda" ? "Generating…" : "Generate / refresh agenda"}
                </button>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <AiMetaRow label="Last run" outcome={lastGen.agenda ?? null} />
                <AiOutcomeBanner outcome={lastGen.agenda ?? null} />
                <WarningsList warnings={lastGen.agenda?.output_warnings ?? []} />
                <AgendaCards artifact={latestAgenda} />
              </div>
            </section>
          ) : null}

          {tab === "account" ? (
            <section className="tenant-panel tenant-review-ai-panel">
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Account manager prep</h2>
                <div className="tenant-review-actions">
                  <button
                    type="button"
                    className="tenant-btn-inline"
                    disabled={!!genBusy}
                    onClick={() =>
                      accessToken &&
                      currentTenantId &&
                      void runGen("notes", () => api.postReviewAccountNotesAi(accessToken, currentTenantId, customerId))
                    }
                  >
                    {genBusy === "notes" ? "…" : "Next conversation"}
                  </button>
                  <button
                    type="button"
                    className="tenant-btn-inline"
                    disabled={!!genBusy}
                    onClick={() =>
                      accessToken &&
                      currentTenantId &&
                      void runGen("script", () => api.postReviewCallScriptAi(accessToken, currentTenantId, customerId))
                    }
                  >
                    {genBusy === "script" ? "…" : "Call script"}
                  </button>
                </div>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <AiMetaRow label="Last run (notes)" outcome={lastGen.notes ?? null} />
                <AiOutcomeBanner outcome={lastGen.notes ?? null} />
                <AiMetaRow label="Last run (script)" outcome={lastGen.script ?? null} />
                <AiOutcomeBanner outcome={lastGen.script ?? null} />
                <CommercialReviewCards detail={detail} className="tenant-review-commerce tenant-review-commerce--compact" />
                <AccountManagerStructuredBlock
                  label="Next conversation"
                  artifact={latestNotes}
                  genWarnings={lastGen.notes?.output_warnings}
                />
                <AccountManagerStructuredBlock
                  label="Call script"
                  artifact={latestScript}
                  genWarnings={lastGen.script?.output_warnings}
                />
              </div>
            </section>
          ) : null}

          {tab === "email" ? (
            <section className="tenant-panel tenant-review-ai-panel">
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Customer email draft</h2>
                <div className="tenant-review-actions">
                  <select
                    className="tenant-review-select tenant-review-select--inline"
                    value={emailTone}
                    onChange={(e) => setEmailTone(e.target.value)}
                    aria-label="Tone"
                  >
                    <option value="professional">Professional</option>
                    <option value="friendly">Friendly</option>
                    <option value="concise">Concise</option>
                  </select>
                  <button
                    type="button"
                    className="tenant-btn-inline"
                    disabled={!!genBusy}
                    onClick={() =>
                      accessToken &&
                      currentTenantId &&
                      void runGen("email", () =>
                        api.postReviewEmailDraftAi(accessToken, currentTenantId, customerId, { tone: emailTone })
                      )
                    }
                  >
                    {genBusy === "email" ? "Generating…" : "Generate / refresh"}
                  </button>
                </div>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <AiMetaRow label="Last run" outcome={lastGen.email ?? null} />
                <AiOutcomeBanner outcome={lastGen.email ?? null} />
                <EmailPanel artifact={latestEmail} liveWarnings={lastGen.email?.output_warnings} />
              </div>
            </section>
          ) : null}

          {tab === "report" ? (
            <section className="tenant-panel tenant-review-ai-panel">
              <div className="tenant-panel-head tenant-review-no-print">
                <h2 className="tenant-panel-title">Customer report</h2>
                <div className="tenant-review-actions">
                  <button
                    type="button"
                    className="tenant-btn-inline"
                    disabled={!!genBusy}
                    onClick={() =>
                      accessToken &&
                      currentTenantId &&
                      void runGen("report", () => api.postReviewCustomerReportAi(accessToken, currentTenantId, customerId))
                    }
                  >
                    {genBusy === "report" ? "Generating…" : "Generate / refresh report"}
                  </button>
                  <button type="button" className="tenant-btn-inline tenant-btn-inline--ghost" onClick={() => window.print()}>
                    Print customer report
                  </button>
                  <Link
                    className="tenant-btn-inline tenant-btn-inline--ghost"
                    to={`/app/reviews?customer_id=${encodeURIComponent(customerId)}&tab=report&view=report`}
                  >
                    Print layout
                  </Link>
                </div>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <AiMetaRow label="Last run" outcome={lastGen.report ?? null} />
                <AiOutcomeBanner outcome={lastGen.report ?? null} />
                <ReportDocument detail={detail} artifact={latestReport} liveWarnings={lastGen.report?.output_warnings} />
              </div>
            </section>
          ) : null}

          {tab === "history" ? (
            <section className="tenant-panel">
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">AI generation history</h2>
                <select
                  className="tenant-review-select tenant-review-select--inline"
                  value={historyType}
                  onChange={(e) => setHistoryType(e.target.value)}
                  aria-label="Filter by type"
                >
                  <option value="">All types</option>
                  <option value="review_agenda">Agenda</option>
                  <option value="customer_email_draft">Email</option>
                  <option value="customer_report">Report</option>
                  <option value="account_manager_notes">Account notes</option>
                  <option value="call_script">Call script</option>
                </select>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <p className="muted">Prior runs are listed newest first. Short summaries are fed into future AI context automatically.</p>
                <ul className="tenant-review-history-list">
                  {history.map((h) => (
                    <li key={h.id} className="tenant-review-history-item">
                      <div className="tenant-review-history-head">
                        <strong>{h.artifact_type}</strong> · {h.status} · {h.created_at ? new Date(h.created_at).toLocaleString() : "—"}
                        {h.output_warnings?.length ? (
                          <span className="tenant-review-history-warn" title={h.output_warnings.join(" · ")}>
                            {h.output_warnings.length} warning{h.output_warnings.length === 1 ? "" : "s"}
                          </span>
                        ) : null}
                        {needsCustomerReviewFromArtifact(h) ? (
                          <span className="tenant-review-history-needs">Needs review</span>
                        ) : null}
                      </div>
                      <div className="muted">{String((h.short_context_json as Record<string, unknown> | undefined)?.summary ?? h.title ?? "")}</div>
                      <div className="muted" style={{ fontSize: "0.78rem" }}>
                        {h.prompt_key ?? "—"} · {h.model_used ?? "—"}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          ) : null}

          {tab === "confidence" ? (
            <section className="tenant-panel">
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Data confidence</h2>
                <Link className="tenant-panel-link" to="/app/data-quality">
                  Data quality
                </Link>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <p className="muted">
                  AI uses connector-sourced customer context only. Gaps below limit what the meeting pack can claim.
                </p>
                <ul className="tenant-list-plain">
                  {dataGaps.map((g) => (
                    <li key={g} className="tenant-rec-card">
                      {g}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
