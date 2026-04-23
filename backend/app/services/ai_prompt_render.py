"""Lightweight prompt rendering (placeholders); extend later for richer templating."""

from __future__ import annotations

import json
import re
from typing import Any


_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render_prompt_template(template: str, variables: dict[str, Any]) -> str:
    """Replace ``{{name}}`` placeholders with JSON-encoded values (strings unquoted)."""

    def _subst(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in variables:
            return m.group(0)
        val = variables[key]
        if isinstance(val, str):
            return val
        return json.dumps(val, ensure_ascii=False, indent=2)

    return _PLACEHOLDER.sub(_subst, template)
