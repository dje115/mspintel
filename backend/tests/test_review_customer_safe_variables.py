"""Customer-facing Review AI variables must not expose internal workspace to the LLM."""

from __future__ import annotations

from app.services.review_ai_output import collect_review_output_warnings
from app.services.ai_task_variable_policy import (
    prepare_llm_variables,
    slim_review_variables_for_customer_facing,
)


def test_slim_customer_variables_use_safe_workspace_only():
    full = {
        "customer": {
            "id": "c1",
            "name": "Bruntingthorpe Engineering",
            "finance_panel": {"secret": True},
            "risk_engine": {"scores": [1, 2]},
        },
        "script_context": {
            "customer": {
                "name": "Bruntingthorpe Engineering",
                "mapping_status": "needs_review",
                "mapping_count": 3,
                "primary_contact": {"name": "Sam", "email": "s@x.com", "external_ref": "ps-99"},
            },
            "msp": {"brand_name": "Contoso MSP"},
            "caller": {"name": "Alex Morgan"},
            "account_context": {"connectors": ["xero"]},
        },
        "open_counts": {"tickets": 1},
        "email_tone": "professional",
        "missing_data_notes": ["needs xero"],
        "previous_ai_artifacts": [{"summary": "old"}],
        "review_workspace": {
            "connector_coverage": {"connected_systems": ["xero"]},
            "finance": {"canonical": True},
            "recommendations": [{"title": "Fix mapping"}],
        },
        "review_workspace_customer_safe": {
            "audience": "external_customer_recipient",
            "customer": {"name": "Bruntingthorpe Engineering"},
            "never_include_terms": ["mapping"],
        },
    }
    slim = slim_review_variables_for_customer_facing(full)
    dumped = str(slim)
    assert "connector_coverage" not in dumped
    assert "finance_panel" not in dumped
    assert "risk_engine" not in dumped
    assert "mapping_status" not in dumped
    assert "external_ref" not in dumped
    assert "account_context" not in dumped
    assert slim["review_workspace"]["audience"] == "external_customer_recipient"
    assert slim["missing_data_notes"] == []
    assert slim["previous_ai_artifacts"] == []
    sc = slim["script_context"]
    assert sc["customer"]["name"] == "Bruntingthorpe Engineering"
    assert sc["customer"]["primary_contact"] == {"name": "Sam", "email": "s@x.com"}


def test_prepare_llm_agenda_splits_safe_and_internal_workspace():
    full = {
        "task": "customer_review_agenda",
        "customer": {"id": "1", "name": "Co", "finance_panel": {"x": 1}},
        "script_context": {
            "customer": {"name": "Co", "mapping_status": "bad", "primary_contact": {"name": "A", "external_ref": "z"}},
            "msp": {"brand_name": "M"},
            "caller": {"name": "Pat"},
        },
        "review_workspace": {"connector_coverage": {"x": 1}, "finance": {"linked": False}},
        "review_workspace_customer_safe": {"audience": "external_customer_recipient", "customer": {"name": "Co"}},
        "previous_ai_artifacts": [{"summary": "Run sync"}],
    }
    llm = prepare_llm_variables("customer_review_agenda", full)
    assert llm["review_workspace"]["audience"] == "external_customer_recipient"
    assert "connector_coverage" in (llm.get("review_workspace_internal") or {})
    dumped = str(llm)
    assert "mapping_status" not in dumped
    assert llm["previous_ai_artifacts"] == []


def test_slim_falls_back_to_full_workspace_when_no_safe_blob():
    full = {
        "customer": {"id": "c1", "name": "Co"},
        "script_context": {"customer": {"name": "Co"}, "msp": {}, "caller": {}},
        "review_workspace": {"analysis_scope": "single_customer_review", "finance": {"x": 1}},
    }
    slim = slim_review_variables_for_customer_facing(full)
    assert slim["review_workspace"] == full["review_workspace"]


def test_collect_warnings_flags_internal_wording_in_customer_safe_output():
    text = '{"subject": "Hi", "body": "Please run Xero sync and resolve mapping review rows."}'
    warns, flags = collect_review_output_warnings(text, text, {"body": "Run Xero sync"}, customer_safe=True)
    assert flags.get("needs_customer_review") is True
    assert any("internal" in w.lower() or "tooling" in w.lower() for w in warns)
