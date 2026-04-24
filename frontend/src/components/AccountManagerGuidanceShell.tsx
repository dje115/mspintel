/**
 * Placeholder shell for AI-driven account-manager guidance.
 * Future: resolved text from AIRuntimeResolver + prompt DB keys listed below.
 * See docs/MSP360_PRODUCT_SPEC.md §20 and docs/AI_CONFIGURATION_AND_PROMPTS.md.
 */
type AccountManagerGuidanceShellProps = {
  /** Short line shown under the title (e.g. account name or workspace context). */
  contextLine?: string;
  /** When true, use a denser layout for marketing / dashboard embeds. */
  compact?: boolean;
};

const PROMPT_KEYS = [
  "account_manager_next_conversation.system",
  "account_manager_call_script.system",
  "customer_review_agenda.system",
  "relationship_health_summary.system",
  "next_best_commercial_conversation.system",
  "event_invite_draft.system",
  "campaign_customer_matching.system"
];

export function AccountManagerGuidanceShell({ contextLine, compact }: AccountManagerGuidanceShellProps) {
  return (
    <section className={`tenant-panel tenant-panel--ai-shell${compact ? " tenant-panel--ai-shell--compact" : ""}`}>
      <div className="tenant-panel-head">
        <div>
          <h2 className="tenant-panel-title">AI account manager guidance</h2>
          {contextLine ? (
            <p className="tenant-ai-shell-context">{contextLine}</p>
          ) : null}
        </div>
        <span className="tenant-badge tenant-badge--muted">Preview</span>
      </div>
      <div className="tenant-panel-body tenant-ai-shell-body">
        <p className="tenant-ai-shell-lead">
          Suggested narrative, talk tracks, and agendas will be generated from the <strong>versioned prompt registry</strong> per
          tenant AI routes—not hardcoded in the UI. No model call is made from this placeholder.
        </p>

        <div className="tenant-ai-shell-grid">
          <article className="tenant-ai-placeholder">
            <h3 className="tenant-ai-placeholder-title">Meeting objective</h3>
            <p className="tenant-ai-placeholder-body muted">
              Example: align on service confidence, confirm roadmap priorities, and agree one commercial follow-up.
            </p>
            <p className="tenant-ai-placeholder-key">Maps to prompt keys such as next_best_commercial_conversation.system</p>
          </article>
          <article className="tenant-ai-placeholder">
            <h3 className="tenant-ai-placeholder-title">Suggested next conversation</h3>
            <p className="tenant-ai-placeholder-body muted">
              Example: open with delivery wins, address open recommendations, propose a QBR date if overdue.
            </p>
            <p className="tenant-ai-placeholder-key">account_manager_next_conversation.system</p>
          </article>
          <article className="tenant-ai-placeholder">
            <h3 className="tenant-ai-placeholder-title">Talking points &amp; short script</h3>
            <ul className="tenant-ai-placeholder-list muted">
              <li>Three bullets tailored to risk, growth, and open pipeline.</li>
              <li>Customer-safe wording for sensitive issues.</li>
              <li>Clear ask and agreed next step.</li>
            </ul>
            <p className="tenant-ai-placeholder-key">account_manager_call_script.system</p>
          </article>
          <article className="tenant-ai-placeholder">
            <h3 className="tenant-ai-placeholder-title">Review / QBR agenda suggestion</h3>
            <p className="tenant-ai-placeholder-body muted">
              Example sections: service summary, risk &amp; mitigation, opportunities, roadmap, action log.
            </p>
            <p className="tenant-ai-placeholder-key">customer_review_agenda.system</p>
          </article>
          <article className="tenant-ai-placeholder">
            <h3 className="tenant-ai-placeholder-title">Event / campaign invite suggestion</h3>
            <p className="tenant-ai-placeholder-body muted">
              Example: invite to backup strategy workshop when protection gaps exist (requires backup telemetry later).
            </p>
            <p className="tenant-ai-placeholder-key">event_invite_draft.system · marketing_event_idea_generation.system</p>
          </article>
          <article className="tenant-ai-placeholder">
            <h3 className="tenant-ai-placeholder-title">Customer follow-up idea</h3>
            <p className="tenant-ai-placeholder-body muted">
              Example: schedule executive touch after repeated high-priority tickets.
            </p>
            <p className="tenant-ai-placeholder-key">relationship_health_summary.system</p>
          </article>
        </div>

        <footer className="tenant-ai-shell-foot muted">
          Registry keys used by these surfaces include: {PROMPT_KEYS.join(", ")}.
        </footer>
      </div>
    </section>
  );
}
