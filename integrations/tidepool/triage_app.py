"""INTEGRATION: TIDEPOOL — the "triage my IdeaInbox" entry point.

Phase 1 is ON-DEMAND ONLY: this runs when invoked, never on a schedule. It wires
the concrete adapters into the engine pipeline, persists the results to the three
tables (survivors saved, obligations routed, killed archived so nothing is
silently discarded), and returns the TriageResult for a surface to render.

Dependencies can be injected for offline testing; by default it uses the live
SharePoint / Anthropic adapters.
"""

from __future__ import annotations

from engine import pipeline
from engine.models import Status
from engine.ports import ActionSink, BusinessState, IdeaStore, Reasoner, TriageResult


def run_triage(
    store: IdeaStore | None = None,
    reasoner: Reasoner | None = None,
    business_state: BusinessState | None = None,
    action_sink: ActionSink | None = None,
    persist: bool = True,
) -> TriageResult:
    # Lazy imports so offline tests can inject fakes without live deps installed.
    if store is None:
        from integrations.tidepool.storage_sharepoint import SharePointIdeaStore
        store = SharePointIdeaStore()
    if reasoner is None:
        from integrations.tidepool.reasoner_anthropic import AnthropicReasoner
        reasoner = AnthropicReasoner()
    if business_state is None:
        from integrations.tidepool.business_state import TidepoolBusinessState
        business_state = TidepoolBusinessState()
    if action_sink is None:
        from integrations.tidepool.action_sink import TidepoolActionSink
        action_sink = action_sink or _default_sink(store)

    ideas = store.list_new()
    result = pipeline.triage(ideas, reasoner, business_state, action_sink)

    if persist:
        for idea in ideas:
            store.save(idea)              # triage fields + status now set
            if idea.status == Status.ARCHIVED:
                store.archive(idea)       # audit row; never silently discarded
    return result


def _default_sink(store):
    from integrations.tidepool.action_sink import TidepoolActionSink
    return TidepoolActionSink(store)
