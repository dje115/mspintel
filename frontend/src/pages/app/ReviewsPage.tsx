import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import type { CustomerDetailResponse, CustomerListItem } from "../../api/types";
import { AccountManagerGuidanceShell } from "../../components/AccountManagerGuidanceShell";
import { useSession } from "../../state/session";
import { formatUsdFromCents } from "../../utils/formatWorkspace";

function FinanceReviewStrip({ detail }: { detail: CustomerDetailResponse }) {
  const fin = detail.finance;
  if (!fin) return null;
  return (
    <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
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

function ReviewAgendaPlaceholder({ customerName }: { customerName: string }) {
  return (
    <section className="tenant-panel">
      <div className="tenant-panel-head">
        <h2 className="tenant-panel-title">Review agenda &amp; notes</h2>
        <span className="tenant-badge tenant-badge--muted">Local notes · future sync</span>
      </div>
      <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
        <p className="muted" style={{ marginTop: 0, fontSize: "0.88rem" }}>
          Draft your QBR or service review flow for <strong>{customerName}</strong>. Later: autosave, shared notes, and AI
          drafts from <code className="tenant-code-inline">customer_review_agenda.system</code>.
        </p>
        <textarea
          className="tenant-review-notes"
          readOnly
          rows={8}
          aria-label="Review agenda placeholder"
          value={`Suggested flow (edit in a future release):\n1. Opening — outcomes since last review\n2. Service delivery — tickets, incidents, CSAT (as data allows)\n3. Risk & mitigation — open recommendations and score drivers\n4. Commercial — pipeline, lost quotes worth revisiting\n5. Roadmap — Microsoft, backup, projects (as connectors land)\n6. Actions — owners and dates\n`}
        />
      </div>
    </section>
  );
}

function NextStepsPlaceholder() {
  return (
    <section className="tenant-panel">
      <div className="tenant-panel-head">
        <h2 className="tenant-panel-title">Suggested next steps after the review</h2>
      </div>
      <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
        <ul className="tenant-list-plain">
          <li className="tenant-rec-card">Log agreed actions in PSA or internal runbook (integration later).</li>
          <li className="tenant-rec-card">Schedule follow-up tasks for owners named in recommendations.</li>
          <li className="tenant-rec-card">Attach recap to the account timeline when activity feed ships.</li>
        </ul>
        <p className="muted" style={{ fontSize: "0.82rem", marginBottom: 0 }}>
          AI can later propose steps from <code className="tenant-code-inline">stalled_work_next_action.system</code> and
          recommendation context.
        </p>
      </div>
    </section>
  );
}

export function ReviewsPage() {
  const { accessToken, currentTenantId } = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const customerId = searchParams.get("customer_id") ?? "";

  const [customerOptions, setCustomerOptions] = useState<CustomerListItem[]>([]);
  const [detail, setDetail] = useState<CustomerDetailResponse | null>(null);
  const [loadListError, setLoadListError] = useState<string | null>(null);
  const [loadDetailError, setLoadDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoadListError(null);
    void api
      .customers(accessToken, currentTenantId, { page: 1, page_size: 120 })
      .then((r) => setCustomerOptions(r.items))
      .catch((e: unknown) => setLoadListError(e instanceof Error ? e.message : "Unable to load accounts"));
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    if (!accessToken || !currentTenantId || !customerId) {
      setDetail(null);
      setLoadDetailError(null);
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
    gaps.push("Microsoft 365, backup telemetry, telephony, and deeper accounting reads will strengthen confidence over time.");
    return gaps;
  }, [detail]);

  const onSelectCustomer = (id: string) => {
    if (!id) {
      searchParams.delete("customer_id");
      setSearchParams(searchParams, { replace: true });
      return;
    }
    navigate(`/app/reviews?customer_id=${encodeURIComponent(id)}`, { replace: true });
  };

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Review &amp; QBR prep</h1>
        <p className="tenant-page-sub">
          Prepare customer reviews, QBRs, and commercial check-ins using live account context where available. Pick an
          account to see health, commercial, relationship, and data-confidence panels — then capture agenda notes
          locally.
        </p>
      </header>

      {!detail && (
        <section className="tenant-panel tenant-panel--accent" style={{ marginBottom: "1.25rem" }}>
          <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
            <p style={{ margin: 0, fontWeight: 600, color: "#0f172a" }}>Above the fold — what this workspace answers</p>
            <ul className="tenant-ai-placeholder-list" style={{ color: "#475569", marginTop: "0.5rem" }}>
              <li>How is this customer doing right now?</li>
              <li>What should we talk about in the upcoming review?</li>
              <li>Which risks and commercial threads deserve airtime?</li>
              <li>What data are we missing so we do not overclaim?</li>
            </ul>
          </div>
        </section>
      )}

      <div className="tenant-review-toolbar">
        <div style={{ flex: "1 1 220px" }}>
          <label htmlFor="review-customer-select">Account for this review</label>
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
          {customerId ? (
            <Link to={`/app/customers/${customerId}`} className="tenant-btn-inline">
              Open Customer 360
            </Link>
          ) : null}
        </div>
      </div>

      {loadDetailError ? <p className="tenant-error">{loadDetailError}</p> : null}

      {customerId && !detail && !loadDetailError ? <div className="tenant-skeleton">Loading account context…</div> : null}

      {!customerId && (
        <>
          <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Quick picks</h2>
              <Link className="tenant-panel-link" to="/app/at-risk">
                From at-risk workspace
              </Link>
            </div>
            <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
              {customerOptions.length === 0 ? (
                <div className="tenant-empty">
                  <p className="tenant-empty-title">No accounts loaded</p>
                  <p>Seed the database or sync your PSA to populate customers.</p>
                </div>
              ) : (
                <div className="tenant-grid tenant-grid--cards-3">
                  {customerOptions.slice(0, 6).map((c) => (
                    <article key={c.id} className="tenant-card">
                      <h3 style={{ marginTop: 0 }}>{c.name}</h3>
                      <p className="tenant-page-sub muted">
                        Risk {c.risk_score ?? "—"} · Attention {c.attention_score ?? "—"}
                      </p>
                      <button type="button" className="tenant-btn-inline" onClick={() => onSelectCustomer(c.id)}>
                        Prepare review
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
          <FinanceReviewStrip detail={detail} />

          <div className="tenant-review-kpi-row" aria-label="Account health at a glance">
            <div className="tenant-review-kpi">
              <p className="tenant-review-kpi-label">Risk</p>
              <p className="tenant-review-kpi-value">{detail.latest_scores?.risk_score ?? "—"}</p>
            </div>
            <div className="tenant-review-kpi">
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

          <div className="tenant-two-col">
            <section className="tenant-panel">
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">What to cover in the review</h2>
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
                <h2 className="tenant-panel-title">Risks &amp; issues</h2>
                <Link className="tenant-panel-link" to={`/app/recommendations?customer_id=${detail.id}`}>
                  Open recommendations
                </Link>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <p className="muted" style={{ marginTop: 0, fontSize: "0.88rem" }}>
                  Status: <strong>{detail.status.split("_").join(" ")}</strong>
                  {detail.owner_name ? (
                    <>
                      {" "}
                      · Owner: <strong>{detail.owner_name}</strong>
                    </>
                  ) : (
                    <> · Owner unassigned</>
                  )}
                </p>
                {detail.recommendations.length === 0 ? (
                  <p className="muted">No open recommendations — confirm delivery stability and latent churn drivers.</p>
                ) : (
                  <ul className="tenant-list-plain">
                    {detail.recommendations.slice(0, 5).map((r) => (
                      <li key={r.id} className="tenant-rec-card">
                        <span className={`tenant-badge ${r.priority === "high" ? "tenant-badge--at_risk" : "tenant-badge--muted"}`}>
                          {r.priority}
                        </span>{" "}
                        {r.summary}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
          </div>

          <div className="tenant-two-col">
            <section className="tenant-panel">
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Commercial opportunities</h2>
                <Link className="tenant-panel-link" to="/app/opportunities">
                  Commercial hub
                </Link>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <p className="tenant-kpi-label">Open opportunities ({detail.opportunities.length})</p>
                {detail.opportunities.length === 0 ? (
                  <p className="muted">None on file — discuss expansion and dormant services verbally.</p>
                ) : (
                  <ul className="tenant-list-plain">
                    {detail.opportunities.slice(0, 4).map((o) => (
                      <li key={o.id} className="tenant-rec-card">
                        {o.title} · {formatUsdFromCents(o.value_cents)} · <span className="muted">{o.status}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="tenant-kpi-label" style={{ marginTop: "0.85rem" }}>
                  Quotes snapshot
                </p>
                {detail.quotes.length === 0 ? (
                  <p className="muted">No quotes — good moment to align on procurement rhythm.</p>
                ) : (
                  <ul className="tenant-list-plain">
                    {detail.quotes.slice(0, 4).map((q) => (
                      <li key={q.id} className="tenant-rec-card">
                        {q.title} · <span className="muted">{q.status}</span>
                        {q.revisit_reason ? <span className="muted"> — {q.revisit_reason}</span> : null}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
            <section className="tenant-panel">
              <div className="tenant-panel-head">
                <h2 className="tenant-panel-title">Relationship &amp; stakeholder coverage</h2>
              </div>
              <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
                <p className="muted" style={{ marginTop: 0 }}>
                  Deep stakeholder maps and “last strategic touch” require richer contact and activity ingestion (PSA +
                  telephony). Until then, use Customer 360 and CRM notes alongside this panel.
                </p>
                <ul className="tenant-list-plain">
                  <li className="tenant-rec-card">Owner on record: {detail.owner_name ?? "— unassigned"}</li>
                  <li className="tenant-rec-card">Future: economic buyer coverage, QBR recency, call volume vs peers.</li>
                  <li className="tenant-rec-card">
                    Prompt direction: <code className="tenant-code-inline">relationship_health_summary.system</code>,{" "}
                    <code className="tenant-code-inline">stakeholder_gap_explanation.system</code>
                  </li>
                </ul>
              </div>
            </section>
          </div>

          <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Data confidence &amp; blind spots</h2>
              <Link className="tenant-panel-link" to="/app/data-quality">
                Data quality workspace
              </Link>
            </div>
            <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
              <ul className="tenant-list-plain">
                {dataGaps.map((g) => (
                  <li key={g} className="tenant-rec-card">
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="tenant-panel">
            <div className="tenant-panel-head">
              <h2 className="tenant-panel-title">Support &amp; service summary</h2>
            </div>
            <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
              <p className="muted" style={{ marginTop: 0 }}>
                <strong>{detail.open_tickets_count}</strong> open ticket(s) in the operational snapshot. Pair this with
                your PSA board for narrative during the review. Ticket ageing and category breakdown ship with deeper sync.
              </p>
            </div>
          </section>

          <AccountManagerGuidanceShell customerId={detail.id} contextLine={`Account: ${detail.name}`} />

          <div className="tenant-two-col">
            <ReviewAgendaPlaceholder customerName={detail.name} />
            <NextStepsPlaceholder />
          </div>
        </>
      ) : null}
    </div>
  );
}
