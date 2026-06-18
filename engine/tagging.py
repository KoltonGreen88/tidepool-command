"""ENGINE — Step A: cluster & tag.

A cheap batch pass. Tags each idea across lenses (financial, product, brand, ops)
and names a theme. Detects repetition across the batch and escalates: a theme
that recurs is "a direction, not a note." Repetition counting is deterministic
(done in Python from the model's themes), so the escalation signal is auditable.
"""

from __future__ import annotations

from engine.models import Idea
from engine.parsing import extract_json
from engine.ports import Reasoner

REPETITION_THRESHOLD = 3  # a theme appearing this many times in-batch is "a direction"

_SYSTEM = (
    "You tag early-stage business ideas for triage. You are terse and concrete. "
    "You output only JSON. No em dashes."
)


def _prompt(ideas: list[Idea]) -> str:
    lines = [
        "Tag each idea below across these lenses where relevant: financial, "
        "product, brand, ops. Assign a short Theme (2-4 words) that groups similar "
        "ideas so repetition can be detected. Tags are free-form and multiple.",
        "",
        "Return JSON: {\"ideas\": [{\"id\": \"...\", \"theme\": \"...\", "
        "\"tags\": [\"...\"]}]}",
        "",
    ]
    for idea in ideas:
        raw = idea.raw_source.strip().replace("\n", " ")
        if len(raw) > 800:
            raw = raw[:800] + " ..."
        lines.append(f'- id={idea.idea_id} source={idea.source_type.value}: {raw}')
    return "\n".join(lines)


def tag_and_cluster(ideas: list[Idea], reasoner: Reasoner) -> list[str]:
    """Mutate each idea with `theme` and `tags`; set `repetition_count`.
    Returns the list of emerging themes (recurring >= REPETITION_THRESHOLD)."""
    if not ideas:
        return []
    raw = reasoner.complete(_SYSTEM, _prompt(ideas), max_tokens=1500)
    data = extract_json(raw)
    by_id = {item.get("id"): item for item in data.get("ideas", [])}

    for idea in ideas:
        item = by_id.get(idea.idea_id, {})
        idea.theme = (item.get("theme") or "").strip()
        idea.tags = [str(t).strip() for t in item.get("tags", []) if str(t).strip()]

    # deterministic repetition counting + escalation
    counts: dict[str, int] = {}
    for idea in ideas:
        key = idea.theme.lower()
        if key:
            counts[key] = counts.get(key, 0) + 1
    emerging: list[str] = []
    for idea in ideas:
        idea.repetition_count = counts.get(idea.theme.lower(), 1)
    for theme_key, n in counts.items():
        if n >= REPETITION_THRESHOLD:
            # surface the original-cased theme
            label = next((i.theme for i in ideas if i.theme.lower() == theme_key), theme_key)
            emerging.append(f"{label} ({n} ideas, a direction not a note)")
    return emerging
