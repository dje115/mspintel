"""Platform default prompt text should not encourage customer-visible meta phrasing."""

from app.services.ai_foundation_seed import PLATFORM_PROMPT_TEXT_OVERRIDES

_TENANT_QBR_KEYS = (
    "customer_review_agenda",
    "customer_review_email_draft",
    "customer_review_report",
    "account_manager_next_conversation",
    "account_manager_call_script",
)


def test_customer_pack_platform_prompts_avoid_prohibited_leak_phrases():
    banned = ("here is the json output", "this is a json output", "this is json")
    for key, text in PLATFORM_PROMPT_TEXT_OVERRIDES.items():
        if not any(k in key for k in _TENANT_QBR_KEYS):
            continue
        low = (text or "").lower()
        for b in banned:
            assert b not in low, f"{key} should not include {b!r}"
