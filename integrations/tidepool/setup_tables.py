"""INTEGRATION: TIDEPOOL — one-time table setup.

Creates the three tables this feature owns (IdeaInbox, OutcomeLog, Archive) in the
IdeaLoss workbook addressed by the canonical STRATEGY_SITE_ID + IDEALOSS_FILE_ID.

Prerequisite: create an empty Excel workbook in the target SharePoint location,
get its drive-item file id, and set IDEALOSS_FILE_ID in Doppler (STRATEGY_SITE_ID
is the OS-wide canonical site id, already present). Then run:

    doppler run -- python -m integrations.tidepool.setup_tables

Each table is created on its own worksheet so the header ranges do not collide.
Safe to re-run: an existing table simply reports back rather than duplicating.
"""

from __future__ import annotations

from integrations.tidepool import config, sharepoint_client as sp

# Each table on its own sheet to avoid header-range collisions.
TABLES = [
    ("IdeaInbox", config.IDEAINBOX_TABLE, config.IDEAINBOX_COLUMNS),
    ("OutcomeLog", config.OUTCOMELOG_TABLE, config.OUTCOMELOG_COLUMNS),
    ("Archive", config.ARCHIVE_TABLE, config.ARCHIVE_COLUMNS),
]


def main() -> None:
    if not sp.has_creds():
        print("Missing Graph credentials. Run under: doppler run -- python -m "
              "integrations.tidepool.setup_tables")
        return
    creds = sp.get_creds()
    if not (creds.get("STRATEGY_SITE_ID") and creds.get("IDEALOSS_FILE_ID")):
        print("STRATEGY_SITE_ID / IDEALOSS_FILE_ID not set. Create an empty workbook "
              "in SharePoint, then set IDEALOSS_FILE_ID in Doppler "
              "(STRATEGY_SITE_ID should already be present OS-wide).")
        return
    print("Creating tables in the IdeaLoss workbook...\n")
    for sheet, table_name, columns in TABLES:
        status = sp.create_table_with_headers(sheet, table_name, columns)
        print(f"  {status}  ({len(columns)} columns)")
    print("\nDone. Verify the workbook has three named tables.")


if __name__ == "__main__":
    main()
