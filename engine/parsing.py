"""ENGINE — small helpers for parsing LLM output and enforcing copy rules.

No external dependencies. The engine asks the Reasoner for JSON and parses it
defensively, since model output can include code fences or stray prose.
"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of model text. Tolerant of code fences and
    surrounding prose. Returns {} if nothing parseable is found."""
    if not text:
        return {}
    cleaned = text.strip()
    # strip ```json ... ``` fences
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # fall back to the first balanced { ... } span
    start = cleaned.find("{")
    if start == -1:
        return {}
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start : i + 1])
                except Exception:
                    return {}
    return {}


def strip_em_dashes(text: str) -> str:
    """Guardrail: no em dashes in generated copy. Replace with a comma+space, and
    normalise the spacing. Covers em dash and the rarer en dash used as a dash."""
    if not text:
        return text
    out = text.replace(" — ", ", ").replace(" – ", ", ")
    out = out.replace("—", ", ").replace("–", ", ")
    return re.sub(r" {2,}", " ", out)
