"""Stable task types and provider taxonomy for AI routing and UI."""

# Task types (code-friendly); align prompt_key prefixes where sensible.
AI_TASK_TYPES: tuple[str, ...] = (
    "recommendation_generation",
    "recommendation_explanation",
    "account_summary",
    "churn_explanation",
    "opportunity_detection",
    "ticket_triage",
    "ticket_rewrite",
    "knowledge_draft",
    "email_draft",
    "risk_summary",
    "customer_review_agenda",
    "account_manager_next_conversation",
    "account_manager_call_script",
    "customer_review_email_draft",
    "customer_review_report",
    "billing_variance_summary",
    "revenue_leakage_explanation",
    "billing_remediation_next_action",
    "underbilling_opportunity",
    "account_confidence_explanation",
    "m365_hygiene_summary",
    "m365_upsell_opportunity",
    "technical_gap_summary",
)

# provider_family: which vendor/protocol family
PROVIDER_FAMILIES: tuple[str, ...] = (
    "openai",
    "azure_openai",
    "anthropic",
    "google",
    "microsoft_copilot",
    "openrouter",
    "ollama",
    "vllm",
    "lm_studio",
    "openai_compatible",
    "custom",
)

# deployment_mode: how/where the model runs (UI + filtering)
DEPLOYMENT_MODES: tuple[str, ...] = (
    "hosted",
    "self_hosted",
    "local",
    "microsoft",
)

PROMPT_SCOPE_PLATFORM = "platform"
PROMPT_SCOPE_TENANT = "tenant"

# Persisted on ai_task_runs.status
AI_RUN_QUEUED = "queued"
AI_RUN_RUNNING = "running"
AI_RUN_SUCCEEDED = "succeeded"
AI_RUN_FAILED = "failed"
AI_RUN_UNAVAILABLE = "unavailable"
AI_RUN_UNSUPPORTED = "unsupported"
AI_RUN_SKIPPED = "skipped"

# Provider families with a runnable OpenAI-compatible HTTP adapter in this release
OPENAI_COMPATIBLE_FAMILIES: frozenset[str] = frozenset(
    {
        "openai",
        "openrouter",
        "ollama",
        "vllm",
        "lm_studio",
        "openai_compatible",
    }
)

# Default platform prompt keys (stable, code-friendly)
DEFAULT_PLATFORM_PROMPT_KEYS: tuple[tuple[str, str, str], ...] = (
    # (prompt_key, task_type, title)
    ("recommendation_generation.system", "recommendation_generation", "Recommendation generation (system)"),
    ("recommendation_explanation.system", "recommendation_explanation", "Recommendation explanation (system)"),
    ("account_summary.system", "account_summary", "Account / Customer 360 summary"),
    ("opportunity_detection.system", "opportunity_detection", "Opportunity detection (system)"),
    ("ticket_triage.system", "ticket_triage", "Ticket triage (system)"),
    ("churn_explanation.system", "churn_explanation", "Churn explanation (system)"),
    ("email_draft.system", "email_draft", "Email draft (system)"),
    ("risk_summary.system", "risk_summary", "Risk summary (system)"),
    ("customer_review_agenda.system", "customer_review_agenda", "Customer review / QBR agenda"),
    (
        "account_manager_next_conversation.system",
        "account_manager_next_conversation",
        "Account manager — next conversation plan",
    ),
    ("account_manager_call_script.system", "account_manager_call_script", "Account manager — call script"),
    ("customer_review_email_draft.system", "customer_review_email_draft", "Customer review — email draft"),
    ("customer_review_report.system", "customer_review_report", "Customer review — customer-facing report"),
    ("billing_variance_summary.system", "billing_variance_summary", "Billing variance summary"),
    ("revenue_leakage_explanation.system", "revenue_leakage_explanation", "Revenue leakage explanation"),
    ("billing_remediation_next_action.system", "billing_remediation_next_action", "Billing remediation next action"),
    ("underbilling_opportunity.system", "underbilling_opportunity", "Underbilling opportunity"),
    ("account_confidence_explanation.system", "account_confidence_explanation", "Account data confidence (finance)"),
    ("m365_hygiene_summary.system", "m365_hygiene_summary", "Microsoft 365 hygiene summary"),
    ("m365_upsell_opportunity.system", "m365_upsell_opportunity", "Microsoft 365 optimisation / upsell"),
    ("technical_gap_summary.system", "technical_gap_summary", "Technical gap summary"),
)
