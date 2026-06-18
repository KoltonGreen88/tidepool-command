"""INTEGRATION: TIDEPOOL — Command Agent surface (tab / HOME widget).

Renders a triage run inside the existing Command Agent (KoltonGreen88/
tidepool-command). Drop `render_triage_tab(st)` into a new tab or HOME section of
that app's app.py. The surface is where the founder already looks; we do not
build a separate place to remember to open.

Honest-rejection UX rules made visible here:
  - The headline reports the rejection (e.g. "8 of 10 killed"), because honest
    rejection is the product, not a side effect.
  - Each survivor shows the case-for AND the kill critique side by side.
  - One-tap actions convert without a dead end.
  - The Cool/Archive audit is one glance away for false-negative spot checks.
  - Outcome logging is one optional tap. The founder is NEVER nagged.
"""

from __future__ import annotations

from engine.ports import TriageResult


def render_triage_tab(st) -> None:
    """Render the on-demand triage tab. `st` is the streamlit module."""
    st.subheader("Idea triage")
    st.caption("On-demand. The job is honest rejection: at most 2 ideas surface per run.")

    if st.button("Triage my IdeaInbox", type="primary"):
        with st.spinner("Reading the inbox, scoring against live business state, killing the rest..."):
            from integrations.tidepool.triage_app import run_triage
            st.session_state["triage_result"] = run_triage()

    result: TriageResult | None = st.session_state.get("triage_result")
    if result is None:
        st.info("Run a triage to see survivors, commitments, and the kill audit.")
        return

    _render_result(st, result)


def _render_result(st, result: TriageResult) -> None:
    killed_n = len(result.killed)
    st.markdown(
        f"**Considered {result.considered}. Surfaced {len(result.surfaced)}. "
        f"Killed {killed_n}. Commitments {len(result.commitments)}.**"
    )
    if result.emerging_themes:
        st.markdown("**Emerging themes (a direction, not a note):**")
        for theme in result.emerging_themes:
            st.markdown(f"- {theme}")

    if result.surfaced:
        st.markdown("### Survivors")
        for pitch in result.surfaced:
            with st.container(border=True):
                st.markdown(f"**{pitch.headline}**")
                for label, text in (
                    ("Financial", pitch.financial_lens),
                    ("Product", pitch.product_lens),
                    ("Brand", pitch.brand_lens),
                ):
                    if text:
                        st.markdown(f"- *{label}:* {text}")
                if pitch.kill_critique:
                    st.markdown(f"> **The case against:** {pitch.kill_critique}")
                cols = st.columns(max(1, len(pitch.one_tap_actions)))
                for col, action in zip(cols, pitch.one_tap_actions):
                    if col.button(action, key=f"{pitch.idea.idea_id}:{action}"):
                        from integrations.tidepool.action_sink import TidepoolActionSink
                        st.success(TidepoolActionSink().convert(pitch.idea, action))
    else:
        st.success("Nothing beat the current plate this run. That is a valid, honest result.")

    if result.commitments:
        st.markdown("### Commitments (carved out before ROI, never killed)")
        for idea in result.commitments:
            st.markdown(f"- **{idea.obligation_type.value}**: {idea.raw_source[:140]}")

    if result.downsized:
        st.markdown("### Downsized / revisit (kernels kept from killed ideas)")
        for idea in result.downsized:
            st.markdown(f"- {idea.kernel_text}")

    if result.resurfaced_watch:
        st.markdown("### Watch list (timing kills that can auto-resurface)")
        for idea in result.resurfaced_watch:
            st.markdown(f"- *{idea.theme or idea.idea_id[:8]}* when: {idea.resurface_when or idea.precondition}")

    with st.expander(f"Cool / Archive audit ({killed_n} killed, spot-check for false negatives)"):
        for idea in result.killed:
            st.markdown(f"- **{idea.theme or idea.idea_id[:8]}**: {idea.kill_reasons}")
