"""
SharePoint read client — copied directly from tidepool-finance-agent/sharepoint_client.py.
Non-negotiable read pattern: Drive/Excel workbook path exclusively.
"""
from __future__ import annotations
import os
import time
from datetime import date, timedelta
from typing import Any
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)
except ImportError:
    pass

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


def _excel_serial_to_str(serial) -> str:
    try:
        if serial == "" or serial is None:
            return ""
        n = int(float(serial))
        if n < 1000:
            return str(serial)
        return (date(1899, 12, 30) + timedelta(days=n)).isoformat()
    except Exception:
        return str(serial)


def _get_creds() -> dict[str, str]:
    keys = [
        "GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET",
        "SHAREPOINT_SITE_ID", "FINANCE_SITE_ID", "STRATEGY_SITE_ID",
        "GIFTING_FILE_ID", "EVENTS_FILE_ID", "CREATOR_FILE_ID",
        "FINANCE_FILE_ID", "FINANCE_SUMMARY_FILE_ID",
        "MEETINGS_FILE_ID", "VIDEO_FILE_ID", "SALES_FILE_ID",
    ]
    creds = {k: os.environ.get(k, "").strip() for k in keys}
    missing = [k for k, v in creds.items() if not v]
    if missing:
        try:
            import streamlit as st
            for k in missing:
                val = st.secrets.get(k, "") or ""
                creds[k] = val.strip()
        except Exception:
            pass
    return creds


def has_sharepoint_creds() -> bool:
    c = _get_creds()
    return all([c.get("GRAPH_TENANT_ID"), c.get("GRAPH_CLIENT_ID"), c.get("GRAPH_CLIENT_SECRET")])


def _get_access_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]
    c = _get_creds()
    tenant_id     = c.get("GRAPH_TENANT_ID", "")
    client_id     = c.get("GRAPH_CLIENT_ID", "")
    client_secret = c.get("GRAPH_CLIENT_SECRET", "")
    if not all([tenant_id, client_id, client_secret]):
        raise RuntimeError("Missing Graph credentials in .env")
    url  = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type":    "client_credentials",
        "client_id":     client_id,
        "client_secret": client_secret,
        "scope":         "https://graph.microsoft.com/.default",
    }
    resp = requests.post(url, data=data, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Token request failed ({resp.status_code}): {resp.text[:300]}")
    payload = resp.json()
    token   = payload.get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in response: {payload}")
    _token_cache["token"]      = token
    _token_cache["expires_at"] = now + 55 * 60
    return token


def read_excel_table(site_id: str, file_id: str, table_name: str,
                     filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
    if not has_sharepoint_creds():
        return []
    try:
        token   = _get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        header_url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drive/items/{file_id}/workbook/tables/{table_name}/headerRowRange"
        )
        hr = requests.get(header_url, headers=headers, timeout=15)
        if hr.status_code == 404:
            return []
        hr.raise_for_status()
        columns = [str(c).strip() for c in hr.json().get("values", [[]])[0]]
        if not columns:
            return []
        rows_url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}"
            f"/drive/items/{file_id}/workbook/tables/{table_name}/rows?$top=500"
        )
        all_value_rows: list[list] = []
        while rows_url:
            rr = requests.get(rows_url, headers=headers, timeout=20)
            if rr.status_code == 404:
                return []
            rr.raise_for_status()
            payload = rr.json()
            for item in payload.get("value", []):
                all_value_rows.extend(item.get("values", []))
            rows_url = payload.get("@odata.nextLink")
        result = []
        for row_vals in all_value_rows:
            padded   = list(row_vals) + [""] * max(0, len(columns) - len(row_vals))
            row_dict = {col: padded[i] for i, col in enumerate(columns)}
            if any(str(v).strip() for v in row_dict.values()):
                result.append(row_dict)
        if filters:
            for col, val in filters.items():
                result = [r for r in result if str(r.get(col, "")).lower() == val.lower()]
        return result
    except Exception:
        return []


OPS_LIVE_STATE_URL = (
    "https://graph.microsoft.com/v1.0/drives/"
    "b!5syyXAVfvUGgFhuFyMoEFLkPI2LXg71Oudeh0sTPzHqDLpOUO7P6QKEGYrAjFE-1"
    "/root:/Ops Agent/live_state.json:/content"
)


def fetch_ops_live_state() -> dict | None:
    if not has_sharepoint_creds():
        return None
    try:
        token   = _get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        resp    = requests.get(OPS_LIVE_STATE_URL, headers=headers, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        import json
        return json.loads(resp.content)
    except Exception:
        return None
