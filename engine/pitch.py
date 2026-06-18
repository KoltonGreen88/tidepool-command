"""ENGINE — Step G: the pitch (survivors only).

Multi-lens framing (financial / product / brand) WITH the kill-pass critique
attached, so the case against sits next to the case for. The founder never sees a
one-sided pitch. One tap converts to a task or a Commitment (actions come from
the ActionSink). No em dashes in generated copy.
"""

from __future__ import annotations

from engine.models import Idea
from engine.parsing import extract_json, strip_em_dashes
from engine.ports import ActionSink, Pitch, Reasoner

_SYSTEM = (
    "You frame a surviving business idea for a busy founder. Three short lenses: "
    "financial, product, brand. Concrete, grounded in the idea and its numbers. "
    "You output only JSON. No em dashes."
)


def _prompt(idea: Idea) -> str:
    return (
        "Frame this surviving idea. Keep each lens to one or two sentences. Omit a "
        "lens if it genuinely does not apply.\n\n"
        f"Idea: {idea.raw_source.strip()}\n"
        f"Pro-case: {idea.pro_case}\n"
        f"Cost: {idea.est_cost_hours} hours, {idea.est_cost_dollars}. "
        f"Outcome metric: {idea.outcome_metric}.\n\n"
        "Return JSON: {\"headline\": \"...\", \"financial\": \"...\", "
        "\"product\": \"...\", \"brand\": \"...\"}"
    )


def compose(idea: Idea, reasoner: Reasoner, action_sink: ActionSink) -> Pitch:
    """Build the survivor's Pitch, attaching the kill critique and one-tap actions."""
    data = extract_json(reasoner.complete(_SYSTEM, _prompt(idea)))
    pitch = Pitch(
        idea=idea,
        headline=strip_em_dashes((data.get("headline") or idea.theme or "Surfaced idea").strip()),
        financial_lens=strip_em_dashes((data.get("financial") or "").strip()),
        product_lens=strip_em_dashes((data.get("product") or "").strip()),
        brand_lens=strip_em_dashes((data.get("brand") or "").strip()),
        kill_critique=idea.kill_reasons,  # already em-dash stripped in killpass
        one_tap_actions=action_sink.available_actions(idea),
    )
    return pitch
