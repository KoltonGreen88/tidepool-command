"""ENGINE — the seams. This file IS the architecture.

The engine never touches a database, a UI, an LLM SDK, or any TIDEPOOL specific
thing directly. It depends only on these abstract ports. Each integration
supplies concrete adapters that implement them.

For the TIDEPOOL reference implementation:
  - IdeaStore     -> SharePoint Excel (IdeaInbox / Archive / OutcomeLog) via Graph
  - Reasoner      -> Anthropic (claude-sonnet-4-6)
  - BusinessState -> live_state.json + Finance/Marketing reads
  - SurfaceTarget -> Command Agent tab / HOME widget
  - ActionSink    -> TIDEPOOL task list + OutcomeLog

If the engine ever imports `msal`, `requests`, `streamlit`, or `anthropic`
directly, the layers have tangled. Stop and route it through a port.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from engine.models import Idea


@runtime_checkable
class IdeaStore(Protocol):
    """Read ideas to triage; write triage results, archive entries, outcomes.

    This feature is the only writer to its own three tables. It never writes to
    any existing OS table.
    """

    def list_new(self, include_test: bool = False) -> list[Idea]:
        """Ideas awaiting triage (Status New), excluding test records by default."""
        ...

    def list_all(self, include_test: bool = False) -> list[Idea]: ...

    def save(self, idea: Idea) -> None:
        """Upsert the idea (its triage fields, status, heat) into IdeaInbox."""
        ...

    def archive(self, idea: Idea) -> None:
        """Append a Cool/Archive audit row. Nothing is ever silently discarded."""
        ...


@runtime_checkable
class Reasoner(Protocol):
    """The LLM the engine thinks with. The engine owns the prompts (the IP);
    the adapter owns the transport. Returns raw text the engine parses."""

    def complete(self, system: str, prompt: str, max_tokens: int = 1200) -> str: ...


@runtime_checkable
class BusinessState(Protocol):
    """Live business reality the rubric scores against and the tournament ranks
    against. Provided by the integration (TIDEPOOL: live_state.json + agents)."""

    def metrics(self) -> dict:
        """Real, current metrics (cash, burn, runway, inventory, pipeline, ROI).
        These are the ONLY numbers the rubric may cite. Never invent."""
        ...

    def top_priorities(self) -> list[str]:
        """The founder's current top priorities. An idea must beat one to advance."""
        ...

    def metric_value(self, metric_name: str) -> str:
        """Look up a named metric's current value, or the UNKNOWN sentinel if the
        agents do not have it (which triggers the rubric demotion)."""
        ...


@runtime_checkable
class OutcomeSink(Protocol):
    """One-tap OPTIONAL outcome logging. The system NEVER prompts or nags."""

    def log_outcome(
        self, idea_id: str, surfaced: bool, executed: bool, outcome: str, metric_moved: str = ""
    ) -> None: ...


@runtime_checkable
class ActionSink(Protocol):
    """Where a one-tap conversion writes its artifact (task or Commitment)."""

    def available_actions(self, idea: Idea) -> list[str]: ...

    def convert(self, idea: Idea, action: str) -> str:
        """Perform the conversion. Returns a human-readable reference."""
        ...


@runtime_checkable
class SurfaceTarget(Protocol):
    """Where survivors (and the commitments/audit) appear. TIDEPOOL: Command Agent."""

    def present(self, result: "TriageResult") -> None: ...


# ---- value objects the pipeline produces (transient, not stored records) ----


@dataclass
class Pitch:
    """A survivor's pitch. Case-for and case-against sit together (Step G)."""

    idea: Idea
    headline: str
    financial_lens: str = ""
    product_lens: str = ""
    brand_lens: str = ""
    kill_critique: str = ""          # the Step E case-against, attached on purpose
    one_tap_actions: list[str] = field(default_factory=list)


@dataclass
class TriageResult:
    """The full output of one triage run."""

    surfaced: list[Pitch] = field(default_factory=list)        # <= budget (Step F)
    commitments: list[Idea] = field(default_factory=list)      # Step C carve-outs
    killed: list[Idea] = field(default_factory=list)           # audited, not discarded
    downsized: list[Idea] = field(default_factory=list)        # enhancement (a) kernels
    resurfaced_watch: list[Idea] = field(default_factory=list) # enhancement (b) timing kills
    emerging_themes: list[str] = field(default_factory=list)   # Step A repetition escalation
    considered: int = 0
