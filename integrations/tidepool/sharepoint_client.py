"""INTEGRATION: TIDEPOOL — SharePoint client (Graph API).

Read pattern COPIED from ~/tidepool-finance-agent/sharepoint_client.py (the
canonical client), extended with the write/upsert/create-table calls this feature
needs for its OWN three new tables (IdeaInbox, Archive, OutcomeLog). It writes to
nothing else. Three-layer principle: Logger writes, SharePoint is truth,
dashboards read; this feature is a reader plus a writer to its own tables.

Auth: MSAL client credentials. Secrets from Doppler locally / Streamlit Cloud
Secrets when deployed. Env var NAMES (never values) are printable via
`diagnostic.py` to confirm loading.
"""

from __future__ import annotations

import os
import time
from datetime import date, timedelta
from typing import Any

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

# Credentials + coordinates. GRAPH_* match the rest of the OS (never AZURE_*).
# STRATEGY_SITE_ID is the OS-wide canonical id for the Strategy and Growth site
# (shared with the other agents); this feature reuses it rather than duplicating
# the GUID. IDEALOSS_FILE_ID points at this feature's own workbook in that site.
CRED_KEYS = [
    "GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET",
    "STRATEGY_SITE_ID", "IDEALOSS_FILE_ID",
]

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


def get_creds() -> dict[str, str]:
    creds = {k: (os.environ.get(k, "") or "").strip() for k in CRED_KEYS}
    missing = [k for k, v in creds.items() if not v]
    if missing:
        try:
            import streamlit as st
            for k in missing:
                creds[k] = (st.secrets.get(k, "") or "").strip()
        except Exception:
            pass
    return creds


def has_creds() -> bool:
    c = get_creds()
    return all([c.get("GRAPH_TENANT_ID"), c.get("GRAPH_CLIENT_ID"), c.get("GRAPH_CLIENT_SECRET")])


def excel_serial_to_str(serial) -> str:
    try:
        if serial == "" or serial is None:
            return ""
        n = int(float(serial))
        if n < 1000:
            return str(serial)
        return (date(1899, 12, 30) + timedelta(days=n)).isoformat()
    except Exception:
        return str(serial)


def _get_access_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]
    c = get_creds()
    tenant_id, client_id, client_secret = (
        c.get("GRAPH_TENANT_ID", ""), c.get("GRAPH_CLIENT_ID", ""), c.get("GRAPH_CLIENT_SECRET", "")
    )
    if not all([tenant_id, client_id, client_secret]):
        raise RuntimeError("Missing Graph credentials (GRAPH_TENANT_ID/CLIENT_ID/CLIENT_SECRET)")
    resp = requests.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Token request failed ({resp.status_code}): {resp.text[:300]}")
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response")
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 55 * 60
    return token


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_get_access_token()}", "Accept": "application/json"}


def _table_base(site_id: str, file_id: str, table_name: str) -> str:
    return f"{GRAPH_ROOT}/sites/{site_id}/drive/items/{file_id}/workbook/tables/{table_name}"


def read_table(table_name: str, include_test: bool = False) -> list[dict[str, Any]]:
    """Read a named table from the IdeaLoss workbook as a list of row dicts.
    Mirrors the canonical reader: excludes TestRecord=TRUE unless asked.
    Never raises; returns [] on any failure so a surface never crashes."""
    if not has_creds():
        return []
    c = get_creds()
    site_id, file_id = c.get("STRATEGY_SITE_ID", ""), c.get("IDEALOSS_FILE_ID", "")
    try:
        base = _table_base(site_id, file_id, table_name)
        hr = requests.get(f"{base}/headerRowRange", headers=_headers(), timeout=15)
        if hr.status_code == 404:
            return []
        hr.raise_for_status()
        columns = [str(col).strip() for col in hr.json().get("values", [[]])[0]]
        if not columns:
            return []
        rows_url = f"{base}/rows?$top=500"
        value_rows: list[list] = []
        while rows_url:
            rr = requests.get(rows_url, headers=_headers(), timeout=20)
            if rr.status_code == 404:
                return []
            rr.raise_for_status()
            payload = rr.json()
            for item in payload.get("value", []):
                value_rows.extend(item.get("values", []))
            rows_url = payload.get("@odata.nextLink")
        result = []
        for vals in value_rows:
            padded = list(vals) + [""] * max(0, len(columns) - len(vals))
            row = {col: padded[i] for i, col in enumerate(columns)}
            if not include_test and str(row.get("TestRecord", "")).strip().upper() == "TRUE":
                continue
            if any(str(v).strip() for v in row.values()):
                result.append(row)
        return result
    except Exception:
        return []


def append_row(table_name: str, columns: list[str], row: dict[str, Any]) -> None:
    """Append one row to a named table. Raises on failure (writes must be loud)."""
    c = get_creds()
    base = _table_base(c.get("STRATEGY_SITE_ID", ""), c.get("IDEALOSS_FILE_ID", ""), table_name)
    values = [[row.get(col, "") for col in columns]]
    resp = requests.post(
        f"{base}/rows/add",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"values": values},
        timeout=20,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"append_row failed ({resp.status_code}): {resp.text[:300]}")


def upsert_row(table_name: str, columns: list[str], key_col: str, row: dict[str, Any]) -> None:
    """Update the row whose key_col matches, else append. Raises on failure."""
    c = get_creds()
    site_id, file_id = c.get("STRATEGY_SITE_ID", ""), c.get("IDEALOSS_FILE_ID", "")
    base = _table_base(site_id, file_id, table_name)
    # find the matching data-row index (0-based over data rows)
    hr = requests.get(f"{base}/headerRowRange", headers=_headers(), timeout=15)
    hr.raise_for_status()
    header = [str(col).strip() for col in hr.json().get("values", [[]])[0]]
    key_idx = header.index(key_col) if key_col in header else -1
    target = -1
    if key_idx >= 0:
        rr = requests.get(f"{base}/rows?$top=500", headers=_headers(), timeout=20)
        rr.raise_for_status()
        i = 0
        for item in rr.json().get("value", []):
            for vals in item.get("values", []):
                if len(vals) > key_idx and str(vals[key_idx]) == str(row.get(key_col, "")):
                    target = i
                    break
                i += 1
            if target >= 0:
                break
    values = [[row.get(col, "") for col in columns]]
    if target >= 0:
        resp = requests.patch(
            f"{base}/rows/itemAt(index={target})",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"values": values},
            timeout=20,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"upsert(update) failed ({resp.status_code}): {resp.text[:300]}")
    else:
        append_row(table_name, columns, row)


def find_test_rows(table_name: str) -> list[dict[str, Any]]:
    """Return the data-row index + IdeaId of every row flagged TestRecord=TRUE.
    The test-flag test matches read_table exactly: str(val).strip().upper()=='TRUE'
    (handles bool True, "TRUE", "True"). Read-only; used to PREVIEW a cleanup
    before deleting. Returns [] if the table or column is absent."""
    c = get_creds()
    base = _table_base(c.get("STRATEGY_SITE_ID", ""), c.get("IDEALOSS_FILE_ID", ""), table_name)
    hr = requests.get(f"{base}/headerRowRange", headers=_headers(), timeout=15)
    if hr.status_code != 200:
        return []
    header = [str(col).strip() for col in hr.json().get("values", [[]])[0]]
    if "TestRecord" not in header:
        return []
    ti = header.index("TestRecord")
    id_i = header.index("IdeaId") if "IdeaId" in header else -1
    rr = requests.get(f"{base}/rows?$top=500", headers=_headers(), timeout=20)
    if rr.status_code != 200:
        return []
    targets: list[dict[str, Any]] = []
    idx = 0
    for item in rr.json().get("value", []):
        for vals in item.get("values", []):
            is_test = len(vals) > ti and str(vals[ti]).strip().upper() == "TRUE"
            if is_test:
                targets.append({
                    "index": idx,
                    "IdeaId": vals[id_i] if 0 <= id_i < len(vals) else "",
                })
            idx += 1
    return targets


def delete_test_rows(table_name: str) -> dict[str, Any]:
    """Delete ONLY rows flagged TestRecord=TRUE from `table_name`. Strictly scoped
    to the test-record convention; never touches a non-test row. Deletes from the
    highest data-row index down so earlier indices do not shift. Raises on any
    delete failure (writes must be loud). Returns {'targeted': n, 'deleted': n}."""
    c = get_creds()
    base = _table_base(c.get("STRATEGY_SITE_ID", ""), c.get("IDEALOSS_FILE_ID", ""), table_name)
    targets = find_test_rows(table_name)
    deleted = 0
    for idx in sorted((t["index"] for t in targets), reverse=True):
        resp = requests.delete(f"{base}/rows/itemAt(index={idx})", headers=_headers(), timeout=20)
        if resp.status_code >= 300:
            raise RuntimeError(f"delete row {idx} failed ({resp.status_code}): {resp.text[:300]}")
        deleted += 1
    return {"targeted": len(targets), "deleted": deleted}


def create_table_with_headers(sheet: str, table_name: str, headers: list[str]) -> str:
    """Create a named table on `sheet` with the given header row. Used once by the
    setup script. Returns a status string. Idempotent-ish: if the table exists,
    Graph returns an error which the caller can treat as 'already there'."""
    c = get_creds()
    site_id, file_id = c.get("STRATEGY_SITE_ID", ""), c.get("IDEALOSS_FILE_ID", "")
    wb = f"{GRAPH_ROOT}/sites/{site_id}/drive/items/{file_id}/workbook"
    h = {**_headers(), "Content-Type": "application/json"}

    # ensure the worksheet exists (ignore error if it already does)
    requests.post(f"{wb}/worksheets/add", headers=h, json={"name": sheet}, timeout=20)

    # write the header row across A1.. so the table has labelled columns
    last_col = _col_letter(len(headers))
    addr = f"{sheet}!A1:{last_col}1"
    rng = requests.patch(
        f"{wb}/worksheets/{sheet}/range(address='{addr}')",
        headers=h, json={"values": [headers]}, timeout=20,
    )
    if rng.status_code >= 300:
        return f"{table_name}: header write failed ({rng.status_code}): {rng.text[:200]}"

    # add the table over that header range, with headers
    add = requests.post(
        f"{wb}/tables/add", headers=h,
        json={"address": addr, "hasHeaders": True}, timeout=20,
    )
    if add.status_code >= 300:
        return f"{table_name}: table add failed or exists ({add.status_code}): {add.text[:200]}"
    new_id = add.json().get("id") or add.json().get("name")
    # rename to the desired table name
    requests.patch(f"{wb}/tables/{new_id}", headers=h, json={"name": table_name}, timeout=20)
    return f"{table_name}: created"


def _col_letter(n: int) -> str:
    """1-based column index to Excel letter (1->A, 27->AA)."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s
