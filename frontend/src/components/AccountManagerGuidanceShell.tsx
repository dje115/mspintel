import { CustomerGuidanceAiPanel } from "./CustomerGuidanceAiPanel";

const STATIC_PROMPT_KEYS = [
  "account_manager_next_conversation.system",
  "account_manager_call_script.system",
  "customer_review_agenda.system",
  "relationship_health_summary.system",
  "next_best_commercial_conversation.system",
  "event_invite_draft.system",
  "campaign_customer_matching.system"
];

type AccountManagerGuidanceShellProps = {
  /** When set, runs real AI tasks for this customer (prompt registry + tenant AI settings). */
  customerId?: string | null;
  contextLine?: string;
  compact?: boolean;
};

/**
 * Without `customerId`: static shell explaining future prompt-registry keys.
 * With `customerId`: delegates to {@link CustomerGuidanceAiPanel} (live GET/POST to `/api/v1/customers/.../ai/...`).
 */
export function AccountManagerGuidanceShell({ customerId, contextLine, compact }: AccountManagerGuidanceShellProps) {
  if (customerId) {
    return <CustomerGuidanceAiPanel customerId={customerId} contextLine={contextLine} compact={!!compact} />;
  }

  return (
    <section className={`tenant-panel tenant-panel--ai-shell${compact ? " tenant-panel--ai-shell--compact" : ""}`}>
      <div className="tenant-panel-head">
        <div>
          <h2 className="tenant-panel-title">AI account manager guidance</h2>
          {contextLine ? <p className="tenant-ai-shell-context">{contextLine}</p> : null}
        </div>
        <span className="tenant-badge tenant-badge--muted">Preview</span>
      </div>
      <div className="tenant-panel-body tenant-ai-shell-body">
        <p className="tenant-ai-shell-lead">
          Select an account to <strong>generate</strong> review agendas, next-conversation plans, and call scripts from
          the versioned prompt registry (same runtime as Customer 360 AI). Planned keys also include:
        </p>
        <ul className="tenant-ai-placeholder-list muted">
          {STATIC_PROMPT_KEYS.map((k) => (
            <li key={k}>
              <code className="tenant-code-inline">{k}</code>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
