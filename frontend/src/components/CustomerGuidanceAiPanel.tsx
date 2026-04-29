import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { AIProductBlockState } from "../api/types";
import { useSession } from "../state/session";
import { TenantAiContextNotice } from "./TenantAiContextNotice";

type GuidanceTask =
  | "customer_review_agenda"
  | "account_manager_next_conversation"
  | "account_manager_call_script";

const TASK_META: Record<GuidanceTask, { title: string; hint: string; promptKey: string }> = {
  customer_review_agenda: {
    title: "Review / QBR agenda",
    hint: "Structured agenda, talking points, and prep checklist for the next customer review.",
    promptKey: "customer_review_agenda.system"
  },
  account_manager_next_conversation: {
    title: "Next conversation plan",
    hint: "Purpose, tone, opening lines, and a clear ask for the next account touch.",
    promptKey: "account_manager_next_conversation.system"
  },
  account_manager_call_script: {
    title: "Call script",
    hint: "Short script for a 10–15 minute check-in or recovery call.",
    promptKey: "account_manager_call_script.system"
  }
};

function statusMessage(s: AIProductBlockState): string | null {
  if (s.status === "not_generated") return "Not generated yet — uses your tenant AI settings and prompt registry.";
  if (s.status === "succeeded") return null;
  if (s.status === "failed") return s.message ?? "Generation failed.";
  if (s.status === "unsupported") return s.message ?? "Provider is not executable in this release.";
  if (s.status === "unavailable") return s.message ?? "AI is not fully configured for this task.";
  if (s.status === "skipped") return s.message ?? "This AI task is disabled for your tenant.";
  if (s.status === "queued" || s.status === "running") return "A run is in progress — try again shortly.";
  return s.message ?? s.status;
}

function normalizeGuidanceText(text: string): string {
  return text
    .replace(/```markdown/gi, "")
    .replace(/```/g, "")
    .replace(/\[Customer Name\]/gi, "the customer")
    .replace(/\[MSP Name\]/gi, "your MSP team")
    .replace(/\[Your Name\]/gi, "your account manager")
    .replace(/\[Owner Name\]/gi, "your account manager")
    .replace(/\[insert [^\]]+\]/gi, "the agreed time")
    .replace(/\[[A-Za-z][A-Za-z\s]{2,}\]/g, "the customer contact")
    .replace(/\*\*/g, "")
    .replace(/^[=-]{3,}$/gm, "")
    .trim();
}

function parseSections(text: string): { title: string; body: string }[] {
  const cleaned = normalizeGuidanceText(text);
  if (!cleaned) return [];
  const lines = cleaned.split("\n");
  const sections: { title: string; body: string }[] = [];
  let currentTitle = "Guidance";
  let currentBody: string[] = [];
  const flush = () => {
    const body = currentBody.join("\n").trim();
    if (body) sections.push({ title: currentTitle, body });
    currentBody = [];
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    const heading = line.match(/^#{1,6}\s+(.+)$/);
    if (heading) {
      flush();
      currentTitle = heading[1].trim();
      continue;
    }
    currentBody.push(line);
  }
  flush();
  return sections.length > 0 ? sections : [{ title: "Guidance", body: cleaned }];
}

function renderSectionBody(body: string): JSX.Element {
  const lines = body
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (lines.length === 0) return <p className="tenant-ai-guidance-output">No details provided.</p>;
  const bulletItems = lines
    .filter((line) => line.startsWith("- ") || line.startsWith("* ") || line.startsWith("+ "))
    .map((line) => line.replace(/^[-*+]\s+/, "").trim());
  const orderedItems = lines
    .filter((line) => /^\d+\.\s+/.test(line))
    .map((line) => line.replace(/^\d+\.\s+/, "").trim());
  const paragraphLines = lines.filter(
    (line) => !line.startsWith("- ") && !line.startsWith("* ") && !line.startsWith("+ ") && !/^\d+\.\s+/.test(line)
  );
  return (
    <div>
      {paragraphLines.map((line, idx) => (
        <p key={`p-${idx}`} className="tenant-ai-guidance-output">
          {line}
        </p>
      ))}
      {bulletItems.length > 0 ? (
        <ul className="tenant-ai-guidance-list">
          {bulletItems.map((line, idx) => (
            <li key={`b-${idx}`}>{line}</li>
          ))}
        </ul>
      ) : null}
      {orderedItems.length > 0 ? (
        <ol className="tenant-ai-guidance-list tenant-ai-guidance-list--ordered">
          {orderedItems.map((line, idx) => (
            <li key={`o-${idx}`}>{line}</li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

function GuidanceBlock({
  customerId,
  task,
  compact
}: {
  customerId: string;
  task: GuidanceTask;
  compact: boolean;
}) {
  const { accessToken, currentTenantId } = useSession();
  const [state, setState] = useState<AIProductBlockState | null>(null);
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const meta = TASK_META[task];

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    try {
      let s: AIProductBlockState;
      if (task === "customer_review_agenda") {
        s = await api.getCustomerReviewAgendaAi(accessToken, currentTenantId, customerId);
      } else if (task === "account_manager_next_conversation") {
        s = await api.getAccountManagerNextConversationAi(accessToken, currentTenantId, customerId);
      } else {
        s = await api.getAccountManagerCallScriptAi(accessToken, currentTenantId, customerId);
      }
      setState(s);
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
      if (task === "customer_review_agenda") {
        await api.postCustomerReviewAgendaAi(accessToken, currentTenantId, customerId);
      } else if (task === "account_manager_next_conversation") {
        await api.postAccountManagerNextConversationAi(accessToken, currentTenantId, customerId);
      } else {
        await api.postAccountManagerCallScriptAi(accessToken, currentTenantId, customerId);
      }
      await load();
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const displayText = state?.status === "succeeded" ? state.text : null;
  const sections = displayText ? parseSections(displayText) : [];
  const loadingInitial = state === null;

  return (
    <article className={`tenant-ai-guidance-block${compact ? " tenant-ai-guidance-block--compact" : ""}`}>
      <div className="tenant-ai-guidance-block-head">
        <div>
          <h3 className="tenant-ai-guidance-block-title">{meta.title}</h3>
          <p className="tenant-ai-guidance-block-hint">{meta.hint}</p>
          <p className="tenant-ai-guidance-block-key">
            <code>{meta.promptKey}</code>
          </p>
        </div>
        <button type="button" className="tenant-btn-primary" disabled={busy || loadingInitial} onClick={() => void onGenerate()}>
          {busy ? "Running…" : displayText ? "Refresh" : "Generate"}
        </button>
      </div>
      {loadingInitial ? <p className="muted">Loading…</p> : null}
      {state?.last_completed_at ? (
        <p className="muted" style={{ fontSize: "0.75rem", marginTop: "0.35rem" }}>
          Last: {new Date(state.last_completed_at).toLocaleString()}
          {state.provider_family ? ` · ${state.provider_family}` : ""}
          {state.model_used ? ` · ${state.model_used}` : ""}
        </p>
      ) : null}
      {state && statusMessage(state) && !displayText ? <p className="tenant-page-sub">{statusMessage(state)}</p> : null}
      {runError ? <p className="tenant-error">{runError}</p> : null}
      {displayText ? (
        <div className="tenant-ai-guidance-output-grid">
          {sections.map((section, idx) => (
            <div key={`${section.title}-${idx}`} className="tenant-ai-guidance-output-card">
              <h4 className="tenant-ai-guidance-output-title">{section.title}</h4>
              {renderSectionBody(section.body)}
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

export function CustomerGuidanceAiPanel({
  customerId,
  contextLine,
  compact = false
}: {
  customerId: string;
  contextLine?: string;
  compact?: boolean;
}) {
  const tasks: GuidanceTask[] = compact
    ? ["account_manager_next_conversation", "account_manager_call_script"]
    : ["customer_review_agenda", "account_manager_next_conversation", "account_manager_call_script"];

  return (
    <section className={`tenant-panel tenant-panel--ai-shell${compact ? " tenant-panel--ai-shell--compact" : ""}`}>
      <div className="tenant-panel-head">
        <div>
          <h2 className="tenant-panel-title">AI account manager guidance</h2>
          {contextLine ? <p className="tenant-ai-shell-context">{contextLine}</p> : null}
        </div>
        <span className="tenant-badge tenant-badge--muted">Live · prompt DB</span>
      </div>
      <div className="tenant-panel-body tenant-ai-shell-body">
        <p className="tenant-ai-shell-lead">
          AI guidance is based on synced PSA, Microsoft 365, and tenant MSP context where available. It may be incomplete
          when connector mappings or source coverage are missing. Runs use versioned prompts, tenant providers, and{" "}
          <code className="tenant-code-inline">ai_task_runs</code> lineage.
        </p>
        <TenantAiContextNotice compact />
        <div className="tenant-ai-guidance-stack">
          {tasks.map((t) => (
            <GuidanceBlock key={t} customerId={customerId} task={t} compact={compact} />
          ))}
        </div>
      </div>
    </section>
  );
}
