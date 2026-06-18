"""ENGINE — Step B: structured ROI rubric (the advocate call).

The model FILLS fields, it does not free-write. It produces the steelman pro-case
plus structured estimates. Crucially, it NAMES the real metric the outcome ties
to but does NOT invent its value: the engine looks the value up from
BusinessState, and if it is missing the rating is demoted to GRAY (unknowns
penalized, never waived). Low-confidence sources (VideoIdeas) are also demoted.

This is a SEPARATE call from the kill-pass (Step E). The advocate cannot grade
its own homework.
"""

from __future__ import annotations

from engine.models import UNKNOWN, Idea, RubricRating
from engine.parsing import extract_json
from engine.ports import BusinessState, Reasoner

_SYSTEM = (
    "You are an advocate building the strongest honest case for an early-stage "
    "business idea, then filling a structured ROI rubric. You are concrete and "
    "you never invent metric values. You output only JSON. No em dashes."
)


def _prompt(idea: Idea, metrics: dict, available_metrics: list[str]) -> str:
    return (
        "Build the steelman pro-case for this idea, then fill the rubric. For the "
        "expected outcome you MUST name which real business metric it would move, "
        "chosen from the available metrics list. Do NOT state a numeric value, the "
        "system fills that from live data.\n\n"
        f"Idea (theme: {idea.theme}; tags: {', '.join(idea.tags)}):\n"
        f"{idea.raw_source.strip()}\n\n"
        f"Available real metrics: {', '.join(available_metrics) or 'none provided'}\n"
        f"Current business snapshot: {metrics}\n\n"
        "Return JSON: {\n"
        '  "pro_case": "the strongest honest case, 2-3 sentences",\n'
        '  "est_cost_hours": "founder hours estimate",\n'
        '  "est_cost_dollars": "dollar estimate or range",\n'
        '  "displaces": "what this pushes off the plate",\n'
        '  "outcome_metric": "one metric name from the available list",\n'
        '  "confidence": "High|Med|Low",\n'
        '  "merit_rating": "green|yellow|red"\n'
        "}"
    )


def score(idea: Idea, reasoner: Reasoner, business_state: BusinessState) -> Idea:
    """Fill the rubric fields on `idea`, applying the demotion rules. Mutates and
    returns the idea."""
    metrics = business_state.metrics()
    # An outcome can only be tied to a numeric metric. Non-numeric snapshot entries
    # (e.g. as-of dates, staleness flags) are context, not selectable ROI metrics.
    available = [k for k, v in metrics.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    data = extract_json(reasoner.complete(_SYSTEM, _prompt(idea, metrics, available)))

    idea.pro_case = (data.get("pro_case") or "").strip()
    idea.est_cost_hours = str(data.get("est_cost_hours") or "").strip()
    idea.est_cost_dollars = str(data.get("est_cost_dollars") or "").strip()
    idea.displaces = (data.get("displaces") or "").strip()
    idea.outcome_metric = (data.get("outcome_metric") or "").strip()
    idea.confidence = (data.get("confidence") or "").strip()

    # never invent the value: look it up, or mark UNKNOWN
    if idea.outcome_metric:
        idea.outcome_value = business_state.metric_value(idea.outcome_metric)
    else:
        idea.outcome_value = UNKNOWN

    merit = (data.get("merit_rating") or "").strip().lower()
    idea.rubric_rating = _rate(idea, merit)
    return idea


def _rate(idea: Idea, merit: str) -> RubricRating:
    """Demotion is deterministic and engine-owned, not left to the model.
    Missing real-metric inputs or a low-confidence source -> GRAY (demoted)."""
    if idea.inputs_missing() or idea.source_is_low_confidence():
        return RubricRating.GRAY
    if merit in ("green", "yellow", "red"):
        return RubricRating(merit)
    return RubricRating.GRAY
