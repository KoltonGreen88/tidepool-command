"""ENGINE — Step D: force-ranking tournament.

No absolute 1-10 scores (they cluster at 7). Each candidate is ranked against the
founder's current top priorities. An idea advances only if it BEATS something
already on the plate. Comparison, not rating, is the mechanism that forces
rejection.
"""

from __future__ import annotations

from engine.models import Idea
from engine.parsing import extract_json
from engine.ports import BusinessState, Reasoner

_SYSTEM = (
    "You force-rank early-stage business ideas against the founder's current "
    "priorities. You do not assign absolute scores. You decide, for each idea, "
    "whether it beats something already on the plate. You are biased toward NO, "
    "because founder time is the scarce resource. You output only JSON. No em dashes."
)


def _prompt(candidates: list[Idea], priorities: list[str], metrics: dict) -> str:
    lines = [
        "Current top priorities (the plate):",
    ]
    for i, p in enumerate(priorities, 1):
        lines.append(f"  {i}. {p}")
    lines += [
        "",
        f"Business snapshot: {metrics}",
        "",
        "For each candidate, decide if it beats one of the current priorities "
        "enough to displace it. Most should NOT.",
        "",
        'Return JSON: {"ranked": [{"id": "...", "beats_plate": true|false, '
        '"vs": "which priority it competes with", "why": "one sentence"}]}',
        "",
        "Candidates:",
    ]
    for idea in candidates:
        raw = idea.raw_source.strip().replace("\n", " ")
        if len(raw) > 400:
            raw = raw[:400] + " ..."
        lines.append(
            f"- id={idea.idea_id} cost_hours={idea.est_cost_hours} "
            f"displaces={idea.displaces} rubric={idea.rubric_rating.value if idea.rubric_rating else '?'}: {raw}"
        )
    return "\n".join(lines)


def force_rank(
    candidates: list[Idea], reasoner: Reasoner, business_state: BusinessState
) -> dict[str, bool]:
    """Return {idea_id: beats_plate}. Candidates not present default to False."""
    if not candidates:
        return {}
    priorities = business_state.top_priorities()
    data = extract_json(
        reasoner.complete(_SYSTEM, _prompt(candidates, priorities, business_state.metrics()))
    )
    beats: dict[str, bool] = {}
    for item in data.get("ranked", []):
        beats[item.get("id")] = bool(item.get("beats_plate"))
    return {idea.idea_id: beats.get(idea.idea_id, False) for idea in candidates}
