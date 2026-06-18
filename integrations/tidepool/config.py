"""INTEGRATION: TIDEPOOL — configuration, table names, and column schemas.

All secrets come from the environment (Doppler locally / Streamlit Cloud Secrets
deployed). Nothing here is committed. Env var NAMES, never values, are printable
via diagnostic.py. GRAPH_* (never AZURE_*) match the rest of the OS.

The three new tables this feature owns live in a single workbook in the Strategy
and Growth site, addressed by the OS-wide canonical STRATEGY_SITE_ID +
IDEALOSS_FILE_ID (this feature's own workbook id).
"""

from __future__ import annotations

import os

# --- Anthropic (matches the Command Agent's model) ---
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# --- The single worksheet the tables sit on, and their named-table identities ---
WORKSHEET = "IdeaLoss"
IDEAINBOX_TABLE = "IdeaInbox"
OUTCOMELOG_TABLE = "OutcomeLog"
ARCHIVE_TABLE = "Archive"

# --- Column orders (source of truth for setup + storage). Order matters for writes. ---
IDEAINBOX_COLUMNS = [
    "IdeaId", "RawSource", "SourceType", "CapturedDate", "Heat", "Theme", "Tags",
    "EstCostHours", "EstCostDollars", "Displaces", "OutcomeMetric", "OutcomeValue",
    "Confidence", "RubricRating", "IsObligation", "ObligationType", "ProCase",
    "KillVerdict", "KillReasons", "IsTimingKill", "Precondition", "ResurfaceWhen",
    "KernelText", "KernelKept", "Status", "CapturedBy", "TestRecord",
]

OUTCOMELOG_COLUMNS = [
    "IdeaId", "Surfaced", "Executed", "Outcome", "MetricMoved", "LoggedDate",
]

ARCHIVE_COLUMNS = [
    "IdeaId", "ArchivedDate", "Heat", "Theme", "KillReasons", "KernelText",
    "Precondition", "ResurfaceWhen", "TestRecord",
]

# --- Current top priorities (the plate) seam ---
# Phase 1: read from live_state.json if it carries a priorities list, else fall
# back to this founder-set default. A dedicated priorities source is a later
# refinement (see PRODUCT_SPEC limitations).
DEFAULT_PRIORITIES = [
    "Extend runway and control burn",
    "Prove DTC repeat purchase on the three current flavors",
    "Grow short-form-driven DTC traffic on the proven channel",
]
