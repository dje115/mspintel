"""Execute Review/QBR AI tasks and persist customer_review_ai_artifacts."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.ai_constants import AI_RUN_SUCCEEDED
from app.models.entities import CustomerReviewAiArtifact
from app.repositories.customer_review_ai_artifacts import CustomerReviewAiArtifactRepository
from app.repositories.customers import CustomerRepository
from app.schemas.review_ai import ReviewAiGenerationResponse
from app.services.ai_execution_service import AIExecutionService
from app.services.review_ai_output import (
    collect_review_output_warnings,
    merge_short_context,
    parse_json_loose,
)
from app.services.review_prompt_guard import assert_review_ai_task_prompt_available
from app.services.review_qbr_context import (
    build_review_qbr_variables,
    build_source_coverage_summary,
    context_hash_for_customer,
)

# Product artefact type -> AI task_type (prompt registry / tenant routes)
ARTIFACT_TASK_TYPES: dict[str, str] = {
    "review_agenda": "customer_review_agenda",
    "account_manager_notes": "account_manager_next_conversation",
    "call_script": "account_manager_call_script",
    "customer_email_draft": "customer_review_email_draft",
    "customer_report": "customer_review_report",
}


def _artifact_title(parsed: dict[str, Any] | None, artifact_type: str, customer_name: str) -> str:
    if not parsed:
        return f"{artifact_type} — {customer_name}"
    for key in ("meeting_title", "title", "subject"):
        v = parsed.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()[:300]
    return f"{artifact_type} — {customer_name}"


class ReviewAiWorkspaceService:
    def __init__(self, db: Session):
        self.db = db
        self.customers = CustomerRepository(db)
        self.artifacts = CustomerReviewAiArtifactRepository(db)
        self.executor = AIExecutionService(db)

    def _ensure_customer(self, tenant_id: UUID, customer_id: UUID) -> None:
        if not self.customers.get_customer(tenant_id, customer_id):
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    def generate_with_caller(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        actor_user_id: UUID | None,
        artifact_type: str,
        caller_name: str | None,
        caller_email: str | None,
        caller_role: str | None,
        email_tone: str | None = None,
    ) -> ReviewAiGenerationResponse:
        self._ensure_customer(tenant_id, customer_id)
        task_type = ARTIFACT_TASK_TYPES.get(artifact_type)
        if not task_type:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown artifact_type")

        assert_review_ai_task_prompt_available(self.db, tenant_id, task_type)

        variables = build_review_qbr_variables(
            self.db,
            tenant_id,
            customer_id,
            caller_name=caller_name,
            caller_email=caller_email,
            caller_role=caller_role,
            email_tone=email_tone,
        )
        # Full internal workspace for DB lineage (coverage, connector snapshot). `AIExecutionService` applies
        # `prepare_llm_variables` so the model does not see this heavy snapshot for customer/hearing tasks.
        workspace_for_audit = variables.get("review_workspace") or {}

        customer_name = str((variables.get("customer") or {}).get("name") or "Customer")
        missing_notes = list(variables.get("missing_data_notes") or [])
        outcome = self.executor.execute(
            tenant_id=tenant_id,
            task_type=task_type,
            variables=variables,
            actor_user_id=actor_user_id,
            customer_id=customer_id,
        )
        detail = workspace_for_audit
        cov_summary = build_source_coverage_summary({"connector_coverage": detail.get("connector_coverage")})
        source_version = context_hash_for_customer(self.db, tenant_id, customer_id)

        customer_safe = artifact_type in (
            "customer_email_draft",
            "customer_report",
            "review_agenda",
            "call_script",
            "account_manager_notes",
        )
        text = outcome.text or ""
        parsed, raw = parse_json_loose(text)
        warnings, quality_flags = collect_review_output_warnings(text, raw, parsed, customer_safe=customer_safe)
        if parsed is None and outcome.status == AI_RUN_SUCCEEDED:
            warnings.append("AI output was not structured JSON — showing raw text; short summary may be partial.")

        conf_notes: list[str] = []
        if isinstance(parsed, dict):
            cn = parsed.get("confidence_notes")
            if isinstance(cn, list):
                conf_notes = [str(x) for x in cn[:8]]
            elif isinstance(cn, str):
                conf_notes = [cn[:400]]

        short_ctx = merge_short_context(
            parsed,
            artifact_type=artifact_type,
            customer_name=customer_name,
            task_type=task_type,
            confidence_notes=conf_notes,
            missing_data=missing_notes,
            quality_flags=quality_flags or None,
        )

        art_status = "succeeded" if outcome.status == AI_RUN_SUCCEEDED else "failed"
        if outcome.status == AI_RUN_SUCCEEDED:
            self.artifacts.supersede_succeeded_same_type(tenant_id, customer_id, artifact_type)

        row = CustomerReviewAiArtifact(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            customer_id=customer_id,
            artifact_type=artifact_type,
            title=_artifact_title(parsed, artifact_type, customer_name),
            status=art_status,
            full_output_json=parsed,
            full_output_text=None if parsed else (raw or text)[:50000],
            short_context_json=short_ctx,
            created_by_user_id=actor_user_id,
            ai_task_run_id=outcome.run_id,
            prompt_key=f"{task_type}.system",
            prompt_version_id=outcome.prompt_version_id,
            provider_family=outcome.provider_family,
            deployment_mode=outcome.deployment_mode,
            model_used=outcome.model_used,
            source_data_version=source_version,
            source_coverage_summary=cov_summary,
            generated_from_connector_state={"connector_coverage": detail.get("connector_coverage")},
            output_warnings=warnings or None,
        )
        self.artifacts.add(row)
        self.db.commit()

        return ReviewAiGenerationResponse(
            run_id=outcome.run_id,
            status=outcome.status,
            task_type=outcome.task_type,
            text=outcome.text,
            message=outcome.message,
            provider_family=outcome.provider_family,
            deployment_mode=outcome.deployment_mode,
            model_used=outcome.model_used,
            prompt_definition_id=outcome.prompt_definition_id,
            prompt_version_id=outcome.prompt_version_id,
            fallback_used=outcome.fallback_used,
            duration_ms=outcome.duration_ms,
            completed_at=outcome.completed_at,
            artifact_id=row.id,
            structured_output=parsed,
            short_context=short_ctx,
            output_warnings=warnings,
        )
