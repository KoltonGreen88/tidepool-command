"""INTEGRATION: TIDEPOOL — IdeaStore + OutcomeSink over SharePoint Excel.

Maps the generic engine `Idea` onto the IdeaInbox columns and back, and writes
the Archive and OutcomeLog tables. Implements engine.ports.IdeaStore and
engine.ports.OutcomeSink. Drive/Excel workbook via Graph only, never Lists.
"""

from __future__ import annotations

from datetime import datetime, timezone

from engine.heat import compute_heat
from engine.models import (
    Heat, Idea, KillVerdict, ObligationType, RubricRating, SourceType, Status,
)
from engine.ports import IdeaStore, OutcomeSink  # noqa: F401 (documents fulfilled contracts)
from integrations.tidepool import config, sharepoint_client as sp

TAG_SEP = "; "


def _b(val: str) -> bool:
    return str(val).strip().upper() == "TRUE"


def _bs(val: bool) -> str:
    return "TRUE" if val else "FALSE"


def _enum(enum_cls, val, default):
    try:
        return enum_cls(str(val).strip()) if str(val).strip() else default
    except ValueError:
        return default


def idea_to_row(idea: Idea) -> dict:
    return {
        "IdeaId": idea.idea_id,
        "RawSource": idea.raw_source,
        "SourceType": idea.source_type.value,
        "CapturedDate": idea.captured_date.isoformat(),
        "Heat": compute_heat(idea).value,
        "Theme": idea.theme,
        "Tags": TAG_SEP.join(idea.tags),
        "EstCostHours": idea.est_cost_hours,
        "EstCostDollars": idea.est_cost_dollars,
        "Displaces": idea.displaces,
        "OutcomeMetric": idea.outcome_metric,
        "OutcomeValue": idea.outcome_value,
        "Confidence": idea.confidence,
        "RubricRating": idea.rubric_rating.value if idea.rubric_rating else "",
        "IsObligation": _bs(idea.is_obligation),
        "ObligationType": idea.obligation_type.value,
        "ProCase": idea.pro_case,
        "KillVerdict": idea.kill_verdict.value if idea.kill_verdict else "",
        "KillReasons": idea.kill_reasons,
        "IsTimingKill": _bs(idea.is_timing_kill),
        "Precondition": idea.precondition,
        "ResurfaceWhen": idea.resurface_when,
        "KernelText": idea.kernel_text,
        "KernelKept": _bs(idea.kernel_kept),
        "Status": idea.status.value,
        "CapturedBy": idea.captured_by,
        "TestRecord": _bs(idea.test_record),
    }


def row_to_idea(row: dict) -> Idea:
    captured = row.get("CapturedDate", "")
    try:
        dt = datetime.fromisoformat(captured) if captured else datetime.now(timezone.utc)
    except ValueError:
        # tolerate Excel serial dates
        dt = datetime.now(timezone.utc)
        s = sp.excel_serial_to_str(captured)
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            pass
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    tags = [t.strip() for t in str(row.get("Tags", "")).split(TAG_SEP.strip()) if t.strip()]
    idea = Idea(
        raw_source=row.get("RawSource", ""),
        source_type=_enum(SourceType, row.get("SourceType"), SourceType.MANUAL),
        captured_date=dt,
        captured_by=row.get("CapturedBy", "unknown") or "unknown",
        test_record=_b(row.get("TestRecord", "")),
    )
    if row.get("IdeaId"):
        idea.idea_id = row["IdeaId"]
    idea.theme = row.get("Theme", "")
    idea.tags = tags
    idea.est_cost_hours = row.get("EstCostHours", "")
    idea.est_cost_dollars = row.get("EstCostDollars", "")
    idea.displaces = row.get("Displaces", "")
    idea.outcome_metric = row.get("OutcomeMetric", "")
    idea.outcome_value = row.get("OutcomeValue", "") or idea.outcome_value
    idea.confidence = row.get("Confidence", "")
    rating = str(row.get("RubricRating", "")).strip()
    idea.rubric_rating = RubricRating(rating) if rating in {r.value for r in RubricRating} else None
    idea.is_obligation = _b(row.get("IsObligation", ""))
    idea.obligation_type = _enum(ObligationType, row.get("ObligationType"), ObligationType.NONE)
    idea.pro_case = row.get("ProCase", "")
    kv = str(row.get("KillVerdict", "")).strip()
    idea.kill_verdict = KillVerdict(kv) if kv in {k.value for k in KillVerdict} else None
    idea.kill_reasons = row.get("KillReasons", "")
    idea.is_timing_kill = _b(row.get("IsTimingKill", ""))
    idea.precondition = row.get("Precondition", "")
    idea.resurface_when = row.get("ResurfaceWhen", "")
    idea.kernel_text = row.get("KernelText", "")
    idea.kernel_kept = _b(row.get("KernelKept", ""))
    idea.status = _enum(Status, row.get("Status"), Status.NEW)
    return idea


class SharePointIdeaStore:
    """IdeaStore + OutcomeSink backed by the IdeaLoss workbook."""

    # --- IdeaStore ---
    def list_new(self, include_test: bool = False) -> list[Idea]:
        return [i for i in self.list_all(include_test) if i.status == Status.NEW]

    def list_all(self, include_test: bool = False) -> list[Idea]:
        rows = sp.read_table(config.IDEAINBOX_TABLE, include_test=include_test)
        return [row_to_idea(r) for r in rows]

    def save(self, idea: Idea) -> None:
        sp.upsert_row(config.IDEAINBOX_TABLE, config.IDEAINBOX_COLUMNS, "IdeaId", idea_to_row(idea))

    def archive(self, idea: Idea) -> None:
        sp.append_row(config.ARCHIVE_TABLE, config.ARCHIVE_COLUMNS, {
            "IdeaId": idea.idea_id,
            "ArchivedDate": datetime.now(timezone.utc).isoformat(),
            "Heat": compute_heat(idea).value,
            "Theme": idea.theme,
            "KillReasons": idea.kill_reasons,
            "KernelText": idea.kernel_text,
            "Precondition": idea.precondition,
            "ResurfaceWhen": idea.resurface_when,
            "TestRecord": _bs(idea.test_record),
        })

    # --- OutcomeSink (one-tap OPTIONAL; the system never nags) ---
    def log_outcome(
        self, idea_id: str, surfaced: bool, executed: bool, outcome: str, metric_moved: str = ""
    ) -> None:
        sp.append_row(config.OUTCOMELOG_TABLE, config.OUTCOMELOG_COLUMNS, {
            "IdeaId": idea_id,
            "Surfaced": _bs(surfaced),
            "Executed": _bs(executed),
            "Outcome": outcome,
            "MetricMoved": metric_moved,
            "LoggedDate": datetime.now(timezone.utc).isoformat(),
        })
