"""ENGINE — the triage Idea record and its vocabulary.

The core data structure of the internal idea-triage advisor. It is
business-agnostic: it knows nothing about TIDEPOOL, SharePoint, or Anthropic.
An integration maps these fields onto its own columns.

Design rules baked in here:
  - RawSource is NEVER paraphrased away. The pitch reasons from the full raw
    text. Losing the raw text loses the idea.
  - Tags are FREE-FORM and multiple, across lenses (financial/product/brand/ops).
  - Unknowns are penalized, never waived: a missing real-metric value demotes the
    rubric rating to GRAY rather than fabricating a number.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Heat(str, Enum):
    """Temperature of an idea, computed from age. A DECAY SIGNAL, NOT a priority.

    Age never promotes an idea. Heat only signals staleness. Priority comes from
    beating the current top priorities (Step D). See engine/heat.py.
    """

    HOT = "Hot"    # 0-7 days
    WARM = "Warm"  # 7-21 days
    COOL = "Cool"  # 21+ days


class SourceType(str, Enum):
    """Where the raw idea came from. Drives the source-confidence demotion."""

    GRANOLA = "granola"        # rich full-text transcript
    TOKSCRIPT = "tokscript"    # rich full-text transcript
    VIDEOIDEAS = "videoideas"  # LOW-CONFIDENCE: compressed key_idea, no raw transcript
    MANUAL = "manual"          # direct IdeaInbox jot
    QUICK_LOG = "quick_log"    # v1.1 seam: spoken into the Logger Quick Log (not yet wired)


# Source types whose raw material is rich enough to trust without demotion.
RICH_SOURCES = {SourceType.GRANOLA, SourceType.TOKSCRIPT, SourceType.MANUAL, SourceType.QUICK_LOG}
# Source types that must be demoted for missing/thin raw material.
LOW_CONFIDENCE_SOURCES = {SourceType.VIDEOIDEAS}


class RubricRating(str, Enum):
    """Step B rating. GRAY mirrors the Sales Agent 'purple for no brief': it means
    inputs are missing and the idea was auto-demoted, not scored on merit."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GRAY = "gray"  # inputs missing -> demoted, cannot be scored on merit


class ObligationType(str, Enum):
    """Step C classification. Anything but NONE bypasses ROI gating."""

    NONE = "none"
    PROMISE = "promise"
    RELATIONSHIP = "relationship"   # e.g. NIL / creator debt
    LEGAL = "legal"
    IN_MOTION = "in_motion"         # already underway


class KillVerdict(str, Enum):
    SURVIVE = "survive"
    KILL = "kill"


class Status(str, Enum):
    NEW = "New"
    TRIAGED = "Triaged"
    SURFACED = "Surfaced"
    CONVERTED = "Converted"
    ARCHIVED = "Archived"


def _now() -> datetime:
    return datetime.now(timezone.utc)


UNKNOWN = "UNKNOWN"  # sentinel for a real-metric value we could not fill from agents


@dataclass
class Idea:
    """A single idea moving through triage.

    Required at intake: `raw_source`. Everything else is filled by the pipeline.
    """

    # --- intake (always present) ---
    raw_source: str                              # verbatim, never paraphrased away
    source_type: SourceType = SourceType.MANUAL
    captured_date: datetime = field(default_factory=_now)
    idea_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    captured_by: str = "unknown"
    source_ref: str = ""                         # url, meeting name, title
    test_record: bool = False

    # --- Step A: cluster & tag ---
    theme: str = ""
    tags: list[str] = field(default_factory=list)
    repetition_count: int = 1                    # how many ideas share this theme in-window

    # --- Step B: ROI rubric (model fills, does not free-write) ---
    pro_case: str = ""                           # the steelman (advocate call)
    est_cost_hours: str = ""                     # founder hours
    est_cost_dollars: str = ""
    displaces: str = ""
    outcome_metric: str = ""                     # the REAL named metric (never invented)
    outcome_value: str = UNKNOWN                 # filled from agents, or UNKNOWN -> demote
    confidence: str = ""                         # High / Med / Low
    rubric_rating: RubricRating | None = None

    # --- Step C: obligation carve-out ---
    is_obligation: bool = False
    obligation_type: ObligationType = ObligationType.NONE

    # --- Step E: adversarial kill-pass ---
    kill_verdict: KillVerdict | None = None
    kill_reasons: str = ""
    # enhancement (a): a downsized survivable kernel inside a killed idea
    kernel_text: str = ""
    kernel_kept: bool = False
    # enhancement (b): a timing kill records the precondition that would flip it
    is_timing_kill: bool = False
    precondition: str = ""                       # what must become true
    resurface_when: str = ""                     # the observable signal to watch

    # --- lifecycle ---
    status: Status = Status.NEW

    # ---- helpers ----

    def source_is_low_confidence(self) -> bool:
        """True when the source lacks rich raw text and must be demoted."""
        return self.source_type in LOW_CONFIDENCE_SOURCES

    def inputs_missing(self) -> bool:
        """True when a real metric value could not be filled -> demote to GRAY."""
        return self.outcome_value == UNKNOWN or not self.outcome_metric

    def survived(self) -> bool:
        return self.kill_verdict == KillVerdict.SURVIVE and not self.is_obligation
