"""ENGINE — the A-G triage pipeline orchestrator.

Runs the scoring pipeline in its load-bearing order and assembles a TriageResult.
The order and the two-call separation are the IP:

  A  tag_and_cluster   batch tagging + repetition escalation
  B  rubric.score      advocate call: pro-case + filled rubric (unknowns -> GRAY)
  C  obligations.classify   carve obligations OUT before any ROI gating
  D  ranking.force_rank force-rank survivors against the current plate
  E  killpass.kill      SEPARATE adversarial call (the skeptic)
  F  budget cap         surface at most BUDGET; the cap forces rejection
  G  pitch.compose      survivors only, with the kill critique attached

Survival requires BOTH beating the plate (D) AND surviving the kill-pass (E).
This mirrors the validated gate, where the advocate (B) and skeptic (E) ran on
every candidate and the skeptic's reasoning powered the audit.

Routing of the two enhancements:
  (a) killed ideas carrying a kernel  -> result.downsized
  (b) killed ideas that are timing kills -> result.resurfaced_watch
Both are still archived. Nothing is silently discarded.
"""

from __future__ import annotations

from engine import killpass, obligations, pitch, ranking, rubric, tagging
from engine.models import Idea, Status
from engine.ports import ActionSink, BusinessState, Reasoner, TriageResult

BUDGET = 2  # Step F hard cap. Surfacing more than this is a failure state.


def triage(
    ideas: list[Idea],
    reasoner: Reasoner,
    business_state: BusinessState,
    action_sink: ActionSink,
    now=None,
) -> TriageResult:
    result = TriageResult(considered=len(ideas))
    if not ideas:
        return result

    # refresh the decay signal (never a priority, just staleness)
    for idea in ideas:
        idea.status = Status.TRIAGED

    # Step A
    result.emerging_themes = tagging.tag_and_cluster(ideas, reasoner)

    # Step B (advocate) on every idea
    for idea in ideas:
        rubric.score(idea, reasoner, business_state)

    # Step C: carve obligations out BEFORE any ROI gating
    candidates: list[Idea] = []
    for idea in ideas:
        obligations.classify(idea, reasoner)
        if idea.is_obligation:
            result.commitments.append(idea)
        else:
            candidates.append(idea)

    # Step D: force-rank the discretionary candidates against the plate
    beats_plate = ranking.force_rank(candidates, reasoner, business_state)

    # Step E: SEPARATE adversarial kill-pass on every candidate (powers the audit)
    survivors: list[Idea] = []
    for idea in candidates:
        killpass.kill(idea, reasoner, business_state)
        if idea.survived() and beats_plate.get(idea.idea_id, False):
            survivors.append(idea)
        else:
            _route_killed(idea, result)

    # Step F: scarcity budget. Rank survivors so the cap keeps the best.
    survivors.sort(key=lambda i: _survivor_sort_key(i), reverse=True)
    surfaced = survivors[:BUDGET]
    overflow = survivors[BUDGET:]
    for idea in overflow:
        # held, not surfaced this run; never silently dropped
        idea.status = Status.TRIAGED

    # Step G: pitch the surfaced survivors, critique attached
    for idea in surfaced:
        idea.status = Status.SURFACED
        result.surfaced.append(pitch.compose(idea, reasoner, action_sink))

    return result


def _route_killed(idea: Idea, result: TriageResult) -> None:
    """A killed idea is archived, and additionally routed by its enhancement
    signals. It is never silently discarded."""
    idea.status = Status.ARCHIVED
    result.killed.append(idea)
    if idea.kernel_kept:
        result.downsized.append(idea)          # enhancement (a)
    if idea.is_timing_kill:
        result.resurfaced_watch.append(idea)   # enhancement (b)


def _survivor_sort_key(idea: Idea):
    """Order survivors for the budget cap. Prefer green over yellow, then higher
    confidence. Deterministic and explainable."""
    rating_rank = {"green": 3, "yellow": 2, "red": 1, "gray": 0}
    conf_rank = {"high": 3, "med": 2, "low": 1}
    r = rating_rank.get(idea.rubric_rating.value if idea.rubric_rating else "gray", 0)
    c = conf_rank.get(idea.confidence.lower(), 0)
    return (r, c)
