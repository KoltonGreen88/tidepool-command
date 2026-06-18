"""ENGINE — the heat mechanic. A DECAY SIGNAL, NOT a priority.

Every idea carries a temperature computed from age:

    HOT   (0-7 days)
    WARM  (7-21 days)
    COOL  (21+ days)

Critical distinction for the triage advisor: heat NEVER promotes an idea. Age
does not make an idea worth doing. Heat only flags staleness, so the founder can
see at a glance that an un-triaged idea is going cold. Priority is decided by the
force-ranking tournament (Step D) and survival by the kill-pass (Step E), not by
temperature.

Pure and deterministic: age in, temperature out. Callers pass `now` so behavior
is testable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from engine.models import Heat, Idea

WARM_AFTER_DAYS = 7
COOL_AFTER_DAYS = 21


def age_in_days(idea: Idea, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    return (now - idea.captured_date).total_seconds() / 86400.0


def compute_heat(idea: Idea, now: datetime | None = None) -> Heat:
    """The temperature from age alone. This is the whole mechanic: no escalation,
    no promotion, just decay."""
    days = age_in_days(idea, now)
    if days < WARM_AFTER_DAYS:
        return Heat.HOT
    if days < COOL_AFTER_DAYS:
        return Heat.WARM
    return Heat.COOL
