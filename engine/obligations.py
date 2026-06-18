"""ENGINE — Step C: obligation carve-out. Runs BEFORE any ROI gating.

Classifies whether an idea is a promise, relationship debt (e.g. NIL / creator
commitments), a legal requirement, or already in motion. If so it BYPASSES ROI
gating and routes to a separate Commitments list. Never silently killed.

This exists because relationship debt looks like a low-ROI chore to a pure ROI
gate. The gate test proved it: "ship the sample bags owed to creators" was killed
by rubric + kill-pass alone. Step C is the interceptor.
"""

from __future__ import annotations

from engine.models import Idea, ObligationType
from engine.parsing import extract_json
from engine.ports import Reasoner

_SYSTEM = (
    "You classify whether a business idea is actually an obligation that must not "
    "be subjected to ROI ranking. You are strict: only true commitments qualify. "
    "You output only JSON. No em dashes."
)

_VALID = {t.value for t in ObligationType}


def _prompt(idea: Idea) -> str:
    return (
        "Classify this idea. Is it an obligation the founder already owes, rather "
        "than a discretionary bet?\n\n"
        f"Idea: {idea.raw_source.strip()}\n\n"
        "Categories:\n"
        "- promise: an explicit commitment made to someone\n"
        "- relationship: relationship or NIL / creator debt owed\n"
        "- legal: a legal or regulatory requirement\n"
        "- in_motion: already underway and stopping would waste sunk work\n"
        "- none: a discretionary idea, NOT an obligation\n\n"
        'Return JSON: {"obligation_type": "promise|relationship|legal|in_motion|none", '
        '"why": "one sentence"}'
    )


def classify(idea: Idea, reasoner: Reasoner) -> Idea:
    """Set `obligation_type` / `is_obligation`. Mutates and returns the idea."""
    data = extract_json(reasoner.complete(_SYSTEM, _prompt(idea)))
    raw = (data.get("obligation_type") or "none").strip().lower()
    otype = ObligationType(raw) if raw in _VALID else ObligationType.NONE
    idea.obligation_type = otype
    idea.is_obligation = otype is not ObligationType.NONE
    return idea
