"""Idempotent seed for AI provider catalog and platform default prompts."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.domain.ai_constants import DEFAULT_PLATFORM_PROMPT_KEYS, PROMPT_SCOPE_PLATFORM
from app.models.entities import (
    AIProvider,
    AIProviderCatalog,
    PromptActivationEvent,
    PromptDefinition,
    PromptVersion,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Richer default system prompts for selected task types (first platform version only).
PLATFORM_PROMPT_TEXT_OVERRIDES: dict[str, str] = {
    "risk_summary": """You are an MSP risk analyst explaining a **heuristic Risk Engine v1** output for one account.

Input JSON includes ``customer.risk_engine`` (risk/attention levels, reason codes, factors, confidence notes) plus operational and finance context.

Output concise **Markdown** with:
1. **Current risk posture** (state this is heuristic, not predictive certainty).
2. **Top factors** (bullet list grounded in provided factors/evidence).
3. **Confidence & blind spots** (explicitly cite missing data or low confidence).
4. **Suggested operator focus this week** (2-4 actions; no fabricated numbers).
""",
    "churn_explanation": """You explain churn-related concern signals for an MSP account from structured JSON.

Rules:
- Treat ``customer.risk_engine`` as heuristic evidence, not a probabilistic churn model.
- Never claim churn probability percentages unless explicitly provided.
- Include a short **What we know / What is uncertain** split.
""",
    "customer_review_agenda": """You are an MSP account leadership assistant preparing a customer review, QBR, or service review.

You receive JSON with customer profile, scores, open recommendations, opportunities, quotes, and recent actions.

Produce concise **Markdown** with these sections:
1. **Meeting objectives** — 2–4 bullets tied to the data (not generic platitudes).
2. **Suggested agenda (45–60 min)** — timeboxed sections (opening, service, risk, commercial, roadmap, close).
3. **Risks & issues to surface** — from scores and recommendations; if data is thin, say what is unknown.
4. **Commercial threads** — pipeline, lost quotes, expansion hooks grounded in the JSON.
5. **Questions to ask the customer** — 5–8 specific questions.
6. **Internal prep checklist** — 4–6 bullets for the MSP team before the meeting.

Stay factual; do not invent metrics not present in the JSON. Use British or neutral MSP English.""",
    "account_manager_next_conversation": """You are an MSP account manager coach.

Input is JSON for one customer account (scores, tickets, recs, pipeline, quotes, actions).

Output **Markdown** with:
- **Purpose** of the next touch (one sentence).
- **Recommended tone** (e.g. consultative, repair, expansion).
- **Opening lines** — exactly 3 short lines the AM can say verbatim.
- **Core talking points** — 3 bullets with evidence from the JSON.
- **One clear ask** for the customer at the end of the call.
- **Follow-up** — what to send or schedule next.

If critical data is missing, add a short **Data gaps** subsection. No hallucinated products or ticket numbers.""",
    "account_manager_call_script": """You are an MSP account manager coach. Input is JSON for one customer.

Write a **short call script** the AM can follow on a 10–15 minute call. Use **Markdown** with:
1. **60-second opener** — rapport + reason for the call.
2. **Value recap** — what the MSP delivers today (only what is inferable from JSON).
3. **Issue / opportunity framing** — one paragraph grounded in scores or recommendations.
4. **Proposed next step** — concrete (meeting, assessment, quote follow-up).
5. **Close** — polite sign-off.

Keep total length under ~250 words. Do not fabricate SLAs, contract terms, or incidents not in the JSON.""",
    "billing_variance_summary": """You summarise **billing variance** for an MSP account from structured JSON only.

Rules:
- Output **Markdown** with: **Headline**, **What the numbers show** (bullet list), **Confidence & blind spots**, **What would strengthen the picture**.
- If finance linkage is missing or ``confidence_level`` is low/medium, say explicitly that conclusions are **hypotheses**, not audit findings.
- Never claim invoice accuracy, legal recoverability, or exact leakage amounts unless present verbatim in JSON.
- Prefer British or neutral MSP English; keep under ~220 words.""",
    "revenue_leakage_explanation": """You explain **possible revenue leakage** for an MSP account using JSON context (billing snapshots, service counts, notes).

Rules:
- **Markdown**: short intro, numbered hypotheses tied to fields, **Unknowns** subsection when data is incomplete.
- Do not accuse the customer of wrongdoing; frame as reconciliation opportunities.
- If canonical finance is absent, state that clearly and avoid quantified leakage.""",
    "billing_remediation_next_action": """You propose **next internal actions** for MSP billing alignment (not customer-facing legal advice).

Input: JSON with finance panel, integrity signals, and account context.

Output **Markdown** with 4–7 concrete internal steps (owners as roles, not invented names). If data is thin, start with discovery steps (data pulls, meetings) before remediation.""",
    "underbilling_opportunity": """You describe **underbilling / mismatch opportunities** conservatively from JSON.

**Markdown** with bullets. Compare billed vs service counts only when both exist; otherwise list what must be collected first.
Never promise upside revenue figures not inferable from the JSON.""",
    "account_confidence_explanation": """You explain **data confidence** for an MSP account from connector-synced canonical data.

Output concise Markdown with:
1. Confirmed evidence (what is directly supported by current synced fields)
2. Missing or stale inputs
3. Confidence impact (high/medium/low with why)
4. Next data-quality actions for AM/service/ops roles

If data comes from demo/mock Connector Lab scenarios, state findings are directional and require verification.""",
    "m365_hygiene_summary": """You are an MSP Microsoft 365 hygiene analyst.

Input JSON can represent either one account or portfolio-level workspace context from connector-synced canonical M365 posture.
Do not invent security/compliance facts that are not in the payload.

Output concise Markdown with these sections:
1. Executive summary
2. Key hygiene findings (confirmed connector-backed observations)
3. Risks and gaps
4. Suggested next actions for service manager/account manager
5. Confidence and missing-data notes

Rules:
- Distinguish confirmed facts vs assumptions.
- Mention connector coverage or mapping incompleteness when relevant.
- If source appears Connector Lab/dev, explicitly label findings as directional/demo.""",
    "m365_upsell_opportunity": """You provide Microsoft 365 optimisation and upsell guidance from connector-synced canonical posture data.

Output concise Markdown:
1. Opportunity summary
2. Top opportunity candidates (with evidence from counts/findings)
3. Customer conversation angles for AM/service manager
4. Confidence and missing-data caveats

Never invent exact savings/revenue figures without explicit numeric evidence.
If data is Connector Lab/dev, label output as directional/demo.""",
    "technical_gap_summary": """You summarise technical gaps using available connector-synced telemetry (M365 and related account context).

Output concise Markdown:
- Confirmed gaps
- Unverified assumptions
- Priority checks to perform next
- Confidence note

Avoid fake precision and call out missing evidence clearly.""",
}


CATALOG_ROWS: list[tuple[str, str, str, str, str, int]] = [
    ("openai_hosted", "openai", "hosted", "OpenAI (API)", "Hosted OpenAI API", 10),
    ("azure_openai_hosted", "azure_openai", "hosted", "Azure OpenAI", "Microsoft Azure-hosted OpenAI", 20),
    ("anthropic_hosted", "anthropic", "hosted", "Anthropic", "Hosted Anthropic API", 30),
    ("google_hosted", "google", "hosted", "Google AI / Gemini", "Hosted Google generative AI", 40),
    ("microsoft_copilot_microsoft", "microsoft_copilot", "microsoft", "Microsoft Copilot / M365", "Microsoft-hosted Copilot-aligned path", 50),
    ("openrouter_hosted", "openrouter", "hosted", "OpenRouter", "OpenRouter multi-model gateway", 60),
    ("ollama_local", "ollama", "local", "Ollama", "Local Ollama runtime", 100),
    ("vllm_self", "vllm", "self_hosted", "vLLM", "Self-hosted vLLM server", 110),
    ("lm_studio_local", "lm_studio", "local", "LM Studio", "LM Studio compatible local endpoint", 120),
    ("openai_compatible_self", "openai_compatible", "self_hosted", "OpenAI-compatible API", "Generic OpenAI-compatible base URL", 130),
    ("custom_self", "custom", "self_hosted", "Custom provider", "Future custom adapter", 200),
]


def ensure_ai_provider_catalog(db: "Session") -> None:
    existing = db.scalar(select(func.count()).select_from(AIProviderCatalog))
    if existing and int(existing) > 0:
        return
    for code, fam, mode, title, desc, sort in CATALOG_ROWS:
        db.add(
            AIProviderCatalog(
                id=uuid.uuid4(),
                code=code,
                provider_family=fam,
                deployment_mode=mode,
                display_name=title,
                description=desc,
                sort_order=sort,
            )
        )
    db.commit()


def ensure_platform_default_prompts(db: "Session") -> None:
    for prompt_key, task_type, title in DEFAULT_PLATFORM_PROMPT_KEYS:
        exists = db.scalars(
            select(PromptDefinition).where(
                PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
                PromptDefinition.tenant_id.is_(None),
                PromptDefinition.prompt_key == prompt_key,
            )
        ).first()
        if exists:
            continue
        d = PromptDefinition(
            id=uuid.uuid4(),
            scope=PROMPT_SCOPE_PLATFORM,
            tenant_id=None,
            prompt_key=prompt_key,
            title=title,
            description=f"Platform default for {prompt_key}",
            task_type=task_type,
            created_by_user_id=None,
            updated_by_user_id=None,
        )
        db.add(d)
        db.flush()
        body = PLATFORM_PROMPT_TEXT_OVERRIDES.get(
            task_type,
            f"You are an MSP intelligence assistant. Task context: {task_type}. Follow tenant policies and produce concise, actionable output.",
        )
        v = PromptVersion(
            id=uuid.uuid4(),
            prompt_definition_id=d.id,
            version_number=1,
            prompt_text=body,
            change_note="Initial platform version",
            created_by_user_id=None,
            is_active=True,
            version_metadata=None,
        )
        db.add(v)
    db.commit()


def ensure_legacy_prompt_aliases(db: "Session") -> None:
    """If older platform keys exist without the canonical route-aligned key, clone active text once."""
    alias_map: list[tuple[str, str, str, str]] = [
        ("customer360.summary", "account_summary.system", "account_summary", "Account / Customer 360 summary"),
    ]
    for old_key, new_key, task_type, title in alias_map:
        has_new = db.scalars(
            select(PromptDefinition).where(
                PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
                PromptDefinition.tenant_id.is_(None),
                PromptDefinition.prompt_key == new_key,
            )
        ).first()
        if has_new:
            continue
        old_def = db.scalars(
            select(PromptDefinition).where(
                PromptDefinition.scope == PROMPT_SCOPE_PLATFORM,
                PromptDefinition.tenant_id.is_(None),
                PromptDefinition.prompt_key == old_key,
            )
        ).first()
        if not old_def:
            continue
        av = db.scalars(
            select(PromptVersion)
            .where(PromptVersion.prompt_definition_id == old_def.id, PromptVersion.is_active.is_(True))
            .limit(1)
        ).first()
        body = av.prompt_text if av else f"You are an MSP intelligence assistant. Task context: {task_type}."
        nd = PromptDefinition(
            id=uuid.uuid4(),
            scope=PROMPT_SCOPE_PLATFORM,
            tenant_id=None,
            prompt_key=new_key,
            title=title,
            description=f"Cloned from legacy key {old_key}",
            task_type=task_type,
            created_by_user_id=None,
            updated_by_user_id=None,
        )
        db.add(nd)
        db.flush()
        nv = PromptVersion(
            id=uuid.uuid4(),
            prompt_definition_id=nd.id,
            version_number=1,
            prompt_text=body,
            change_note=f"Alias of {old_key}",
            created_by_user_id=None,
            is_active=True,
            version_metadata=None,
        )
        db.add(nv)
        db.flush()
        db.add(
            PromptActivationEvent(
                id=uuid.uuid4(),
                prompt_definition_id=nd.id,
                prompt_version_id=nv.id,
                tenant_id=None,
                actor_user_id=None,
                event_kind="platform_alias_created",
                note=None,
            )
        )
    db.commit()


def ensure_demo_tenant_ai_provider(db: "Session", tenant_id: uuid.UUID) -> None:
    """Attach catalog metadata to the first tenant provider row when missing."""
    row = db.scalars(select(AIProvider).where(AIProvider.tenant_id == tenant_id).limit(1)).first()
    if row and not row.provider_family:
        row.provider_family = "openai_compatible"
        row.deployment_mode = "self_hosted"
        row.catalog_code = "openai_compatible_self"
        row.display_label = row.display_label or "AI Provider (demo)"
        row.is_enabled = True
        db.commit()
