import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { AIProductBlockState } from "../api/types";
import { useSession } from "../state/session";
import { TenantAiContextNotice } from "./TenantAiContextNotice";

type TaskKey = "account_summary" | "risk_summary" | "churn_explanation";

const LABELS: Record<TaskKey, { title: string; hint: string }> = {
  account_summary: {
    title: "AI account summary",
    hint: "Synthesizes scores, pipeline, and open recommendations for this account."
  },
  risk_summary: {
    title: "AI risk narrative",
    hint: "Explains risk signals in plain language for delivery and exec review."
  },
  churn_explanation: {
    title: "AI churn lens",
    hint: "Surfaces churn-related patterns from the same structured context (not a prediction of churn)."
  }
};

function statusMessage(s: AIProductBlockState): string | null {
  if (s.status === "not_generated") return "Not generated yet — run when you are ready (uses your tenant AI settings).";
  if (s.status === "succeeded") return null;
  if (s.status === "failed") return s.message ?? "Generation failed.";
  if (s.status === "unsupported") return s.message ?? "Provider is not executable in this release.";
  if (s.status === "unavailable") return s.message ?? "AI is not fully configured for this task.";
  if (s.status === "skipped") return s.message ?? "This AI task is disabled for your tenant.";
  if (s.status === "queued" || s.status === "running") return "A run is in progress or was interrupted — try again shortly.";
  return s.message ?? s.status;
}

function AiBlock(props: { customerId: string; task: TaskKey; emphasize?: boolean }) {
  const { customerId, task, emphasize } = props;
  const { accessToken, currentTenantId } = useSession();
  const [state, setState] = useState<AIProductBlockState | null>(null);
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    try {
      if (task === "account_summary") {
        setState(await api.getCustomerAccountSummaryAi(accessToken, currentTenantId, customerId));
      } else if (task === "risk_summary") {
        setState(await api.getCustomerRiskSummaryAi(accessToken, currentTenantId, customerId));
      } else {
        setState(await api.getCustomerChurnExplanationAi(accessToken, currentTenantId, customerId));
      }
    } catch {
      setState({
        status: "failed",
        message: "Unable to load AI state.",
        text: null,
        run_id: null,
        last_completed_at: null,
        provider_family: null,
        model_used: null,
        prompt_version_id: null
      });
    }
  }, [accessToken, currentTenantId, customerId, task]);

  useEffect(() => {
    void load();
  }, [load]);

  const onGenerate = async () => {
    if (!accessToken || !currentTenantId) return;
    setBusy(true);
    setRunError(null);
    try {
      if (task === "account_summary") {
        await api.postCustomerAccountSummaryAi(accessToken, currentTenantId, customerId);
      } else if (task === "risk_summary") {
        await api.postCustomerRiskSummaryAi(accessToken, currentTenantId, customerId);
      } else {
        await api.postCustomerChurnExplanationAi(accessToken, currentTenantId, customerId);
      }
      await load();
      setRunError(null);
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const meta = LABELS[task];
  const displayText = state?.status === "succeeded" ? state.text : null;
  const loadingInitial = state === null;

  return (
    <article
      className="tenant-card"
      style={{
        marginBottom: "1rem",
        border: emphasize ? "1px solid rgba(14, 165, 164, 0.35)" : undefined
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", flexWrap: "wrap" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "1.05rem" }}>{meta.title}</h3>
          <p className="tenant-page-sub" style={{ marginTop: "0.25rem", marginBottom: 0 }}>
            {meta.hint}
          </p>
        </div>
        <button
          type="button"
          className="tenant-btn-primary"
          style={{ alignSelf: "flex-start" }}
          disabled={busy || loadingInitial}
          onClick={() => void onGenerate()}
        >
          {busy ? "Running…" : displayText ? "Refresh" : "Generate"}
        </button>
      </div>
      {loadingInitial ? (
        <p className="tenant-skeleton" style={{ marginTop: "0.65rem", marginBottom: 0 }}>
          Loading AI state…
        </p>
      ) : null}
      {state?.last_completed_at ? (
        <p className="muted" style={{ fontSize: "0.78rem", marginTop: "0.5rem" }}>
          Last completed: {new Date(state.last_completed_at).toLocaleString()}
          {state.provider_family ? ` · ${state.provider_family}` : ""}
          {state.model_used ? ` · ${state.model_used}` : ""}
        </p>
      ) : null}
      {state && statusMessage(state) && !displayText ? (
        <p className="tenant-page-sub" style={{ marginTop: "0.65rem", color: "#64748b" }}>
          {statusMessage(state)}
        </p>
      ) : null}
      {runError ? (
        <p className="tenant-error" style={{ marginTop: "0.65rem" }}>
          {runError}
        </p>
      ) : null}
      {displayText ? (
        <div
          className="tenant-rec-card"
          style={{ marginTop: "0.75rem", whiteSpace: "pre-wrap", fontSize: "0.92rem", lineHeight: 1.45 }}
        >
          {displayText}
        </div>
      ) : null}
    </article>
  );
}

export function CustomerAiInsights(props: { customerId: string; highlight?: "risk" | null }) {
  const { customerId, highlight } = props;
  return (
    <section className="tenant-panel" id="customer-ai-insights">
      <div className="tenant-panel-head">
        <h2 className="tenant-panel-title">AI insights</h2>
      </div>
      <div className="tenant-panel-body" style={{ padding: "1rem 1.1rem" }}>
        <p className="tenant-page-sub" style={{ marginTop: 0 }}>
          Outputs use your tenant&apos;s configured providers and versioned prompts. If generation fails, check{" "}
          <strong>AI engines</strong> under Administration — nothing here is mocked.
        </p>
        <TenantAiContextNotice compact />
        <AiBlock customerId={customerId} task="account_summary" />
        <AiBlock customerId={customerId} task="risk_summary" emphasize={highlight === "risk"} />
        <AiBlock customerId={customerId} task="churn_explanation" />
      </div>
    </section>
  );
}
