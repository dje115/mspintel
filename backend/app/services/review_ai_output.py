"""Parse AI assistant output, build short_context fallbacks, detect unsafe placeholders."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

_PLACEHOLDER_PATTERNS = (
    r"\[Customer Name\]",
    r"\[Your Name\]",
    r"\[MSP Name\]",
    r"<customer>",
    r"\[CLIENT NAME\]",
    r"\[Company Name\]",
)

_FENCE_RE = re.compile(r"^```(?:json|markdown)?\s*", re.IGNORECASE)


def strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = _FENCE_RE.sub("", t)
        if t.endswith("```"):
            t = t[: t.rfind("```")].strip()
    return t.strip()


def parse_json_loose(text: str) -> tuple[dict[str, Any] | None, str]:
    """Return (dict, raw_text). If JSON parse fails, dict is None."""
    raw = (text or "").strip()
    if not raw:
        return None, ""
    candidate = strip_code_fences(raw)
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj, raw
    except json.JSONDecodeError:
        pass
    return None, raw


def detect_output_warnings(text: str, *, customer_safe: bool) -> list[str]:
    warnings: list[str] = []
    if not text:
        return warnings
    for pat in _PLACEHOLDER_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            warnings.append("Unresolved placeholder-style tokens detected — review before customer use.")
            break
    if customer_safe and re.search(r"Connector Lab", text, flags=re.IGNORECASE):
        warnings.append("Connector Lab reference in customer-facing copy — rephrase for production.")
    if "```" in text:
        warnings.append("Code-fence markers present — output may need cleanup.")
    return warnings


def merge_short_context(
    parsed: dict[str, Any] | None,
    *,
    artifact_type: str,
    customer_name: str,
    task_type: str,
    confidence_notes: list[str],
    missing_data: list[str],
) -> dict[str, Any]:
    """Prefer model-provided short_context; otherwise build a compact fallback."""
    sc: dict[str, Any] | None = None
    if parsed and isinstance(parsed.get("short_context"), dict):
        sc = dict(parsed["short_context"])
    base: dict[str, Any] = {
        "artifact_type": artifact_type,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "customer_name": customer_name,
        "summary": None,
        "key_points": [],
        "recommended_actions": [],
        "open_questions": [],
        "customer_safe_topics": [],
        "internal_only_notes": [],
        "confidence_level": None,
        "missing_data": list(missing_data)[:12],
    }
    if sc:
        for k in (
            "summary",
            "key_points",
            "recommended_actions",
            "open_questions",
            "customer_safe_topics",
            "internal_only_notes",
            "confidence_level",
            "missing_data",
        ):
            if k in sc and sc[k] is not None:
                base[k] = sc[k]
    if not base.get("summary"):
        title_bits: list[str] = []
        if parsed:
            for key in ("meeting_title", "title", "subject"):
                v = parsed.get(key)
                if isinstance(v, str) and v.strip():
                    title_bits.append(v.strip()[:160])
                    break
        base["summary"] = (
            " ".join(title_bits)
            if title_bits
            else f"Generated {artifact_type.replace('_', ' ')} for {customer_name} ({task_type})."
        )
    if confidence_notes and not base.get("confidence_level"):
        base["confidence_level"] = "see_notes"
    if confidence_notes:
        notes = list(base.get("internal_only_notes") or [])
        notes.extend(confidence_notes[:5])
        base["internal_only_notes"] = notes[:12]
    # Cap list sizes for prompt re-use
    for k in ("key_points", "recommended_actions", "open_questions", "customer_safe_topics", "internal_only_notes"):
        v = base.get(k)
        if isinstance(v, list) and len(v) > 12:
            base[k] = v[:12]
    if isinstance(base.get("summary"), str) and len(base["summary"]) > 500:
        base["summary"] = base["summary"][:497] + "..."
    return base
