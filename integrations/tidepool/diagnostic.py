"""INTEGRATION: TIDEPOOL — startup diagnostic.

Confirms secrets are LOADING by printing env var NAMES and presence, NEVER
values. Guardrail: never print a secret value. Run with:

    doppler run -- python -m integrations.tidepool.diagnostic
"""

from __future__ import annotations

import os

from integrations.tidepool import config

# Names this feature expects. Values are never printed.
EXPECTED = [
    "GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET",
    "STRATEGY_SITE_ID", "IDEALOSS_FILE_ID",
    "ANTHROPIC_API_KEY",
    # optional: live metrics for the rubric (degrade gracefully if absent)
    "FINANCE_SITE_ID", "FINANCE_SUMMARY_FILE_ID", "FINANCE_FILE_ID", "LIVE_STATE_URL",
]


def main() -> None:
    print("IDEA LOSS diagnostic. Printing NAMES and presence only, never values.\n")
    for name in EXPECTED:
        present = bool((os.environ.get(name, "") or "").strip())
        print(f"  {name:<24} {'present' if present else 'MISSING'}")
    print()
    print(f"  ANTHROPIC_MODEL          = {config.ANTHROPIC_MODEL}")
    print(f"  worksheet/tables         = {config.WORKSHEET}: "
          f"{config.IDEAINBOX_TABLE}, {config.OUTCOMELOG_TABLE}, {config.ARCHIVE_TABLE}, "
          f"{config.CASHSTATE_TABLE}")


if __name__ == "__main__":
    main()
