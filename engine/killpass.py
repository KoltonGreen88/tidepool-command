"""ENGINE — Step E: adversarial kill-pass. SEPARATE CALL. NON-NEGOTIABLE.

A fresh-context call whose only job is to KILL the idea. It is given the idea,
its pro-case, and the live business state, and asked for the cheapest reason this
wastes the founder's time, the real cost, the downside, and what it displaces.

Pitch generation (the Step B advocate) and this kill-pass MUST be separate calls
so the model cannot rationalize its own pitch. This is why `score()` and
`kill()` never share a context.

The kill-pass also emits the two enhancement signals the gate test surfaced:
  (a) KERNEL: a downsized survivable version worth keeping even when the full
      idea dies (TikTok Shop buildout dies, a minimal creator-linked test lives).
  (b) TIMING: whether the kill is "not yet" rather than "no", and the precondition
      that would flip the verdict (Meta ads automation killed UNTIL a real CAC
      exists), so the idea can auto-resurface.
"""

from __future__ import annotations

from engine.models import Idea, KillVerdict
from engine.parsing import extract_json, strip_em_dashes
from engine.ports import BusinessState, Reasoner

_SYSTEM = (
    "You are the skeptic. Your job is to KILL business ideas, not to flatter them. "
    "For an early-stage two-person brand, founder hours and cash are the scarcest "
    "resources, so the default is NO. Find the cheapest reason this wastes the "
    "founder's time. Be specific and structural, never generic. You also notice "
    "when a kill is really a 'not yet' (a timing kill with a precondition) and "
    "when a smaller version of a killed idea is still worth keeping (a kernel). "
    "You output only JSON. No em dashes."
)


def _prompt(idea: Idea, metrics: dict) -> str:
    return (
        "Here is an idea and the strongest case its advocate made. Try to kill it.\n\n"
        f"Idea: {idea.raw_source.strip()}\n"
        f"Advocate pro-case: {idea.pro_case}\n"
        f"Estimated cost: {idea.est_cost_hours} hours, {idea.est_cost_dollars}\n"
        f"Claims to displace: {idea.displaces}\n"
        f"Live business snapshot: {metrics}\n\n"
        "Return JSON:\n"
        "{\n"
        '  "verdict": "kill|survive",\n'
        '  "cheapest_reason": "the cheapest reason it wastes time, one sentence",\n'
        '  "real_cost": "the true cost, naming the scarce resource",\n'
        '  "downside": "the downside case",\n'
        '  "displaces": "what it actually displaces",\n'
        '  "has_kernel": true|false,\n'
        '  "kernel_text": "a downsized survivable version, or empty",\n'
        '  "is_timing_kill": true|false,\n'
        '  "precondition": "what must become true to revisit, or empty",\n'
        '  "resurface_when": "the observable signal to watch, or empty"\n'
        "}"
    )


def kill(idea: Idea, reasoner: Reasoner, business_state: BusinessState) -> Idea:
    """Run the adversarial pass. Sets verdict, reasons, kernel, and timing fields.
    Mutates and returns the idea."""
    data = extract_json(reasoner.complete(_SYSTEM, _prompt(idea, business_state.metrics())))

    verdict = (data.get("verdict") or "kill").strip().lower()
    idea.kill_verdict = KillVerdict.SURVIVE if verdict == "survive" else KillVerdict.KILL

    reasons = " ".join(
        s for s in [
            data.get("cheapest_reason", ""),
            f"Real cost: {data.get('real_cost', '')}." if data.get("real_cost") else "",
            f"Downside: {data.get('downside', '')}." if data.get("downside") else "",
            f"Displaces: {data.get('displaces', '')}." if data.get("displaces") else "",
        ] if s
    ).strip()
    idea.kill_reasons = strip_em_dashes(reasons)

    # enhancement (a): kernel-spawning kills
    idea.kernel_kept = bool(data.get("has_kernel")) and bool(data.get("kernel_text"))
    idea.kernel_text = strip_em_dashes((data.get("kernel_text") or "").strip()) if idea.kernel_kept else ""

    # enhancement (b): precondition-resurface for timing kills
    idea.is_timing_kill = bool(data.get("is_timing_kill"))
    idea.precondition = strip_em_dashes((data.get("precondition") or "").strip()) if idea.is_timing_kill else ""
    idea.resurface_when = strip_em_dashes((data.get("resurface_when") or "").strip()) if idea.is_timing_kill else ""
    return idea
