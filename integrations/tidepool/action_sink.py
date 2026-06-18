"""INTEGRATION: TIDEPOOL — ActionSink.

The one-tap conversions a surfaced pitch offers, so the pitch never dead-ends.
The engine owns the CONCEPT of one-tap conversion; this owns WHERE it writes.

Phase 1 keeps the write side deliberately thin: converting marks the idea's
status and (optionally, never nagged) records an OutcomeLog row. A dedicated
TIDEPOOL task table can be wired later without touching the engine.
"""

from __future__ import annotations

from engine.models import Idea, ObligationType, Status
from engine.ports import ActionSink  # noqa: F401 (documents the fulfilled contract)
from integrations.tidepool.storage_sharepoint import SharePointIdeaStore


class TidepoolActionSink:
    def __init__(self, store: SharePointIdeaStore | None = None) -> None:
        self.store = store or SharePointIdeaStore()

    def available_actions(self, idea: Idea) -> list[str]:
        if idea.is_obligation:
            return ["Add to Commitments", "Mark actioned"]
        actions = ["Convert to task", "Mark actioned"]
        if idea.kernel_kept:
            actions.append("Keep the downsized kernel")
        return actions

    def convert(self, idea: Idea, action: str) -> str:
        """Perform a one-tap conversion. Returns a human-readable reference."""
        if action == "Mark actioned":
            idea.status = Status.CONVERTED
            self.store.save(idea)
            # one-tap OPTIONAL outcome record; never prompted for, just captured
            self.store.log_outcome(idea.idea_id, surfaced=True, executed=True, outcome="Marked actioned")
            return f"Marked actioned: {idea.theme or idea.idea_id[:8]}"
        if action == "Add to Commitments":
            idea.obligation_type = (
                idea.obligation_type if idea.is_obligation else ObligationType.PROMISE
            )
            idea.is_obligation = True
            idea.status = Status.CONVERTED
            self.store.save(idea)
            return f"Routed to Commitments: {idea.theme or idea.idea_id[:8]}"
        if action == "Convert to task":
            idea.status = Status.CONVERTED
            self.store.save(idea)
            self.store.log_outcome(idea.idea_id, surfaced=True, executed=False, outcome="Converted to task")
            return f"Converted to task: {idea.theme or idea.idea_id[:8]}"
        if action == "Keep the downsized kernel":
            # the kernel lives on the record; keeping it just leaves it un-archived
            idea.status = Status.TRIAGED
            self.store.save(idea)
            return f"Kept kernel: {idea.kernel_text[:60]}"
        return f"Unknown action: {action}"
