"""INTEGRATION: TIDEPOOL — BusinessState adapter.

Feeds the rubric (Step B) and the force-ranking tournament (Step D) with REAL,
current metrics and the founder's current priorities. Reads the same live sources
the other agents use: FinanceSummary (cash/burn/runway) and live_state.json
(inventory). Implements engine.ports.BusinessState.

Hard rule: this is the ONLY place the engine gets numbers. If a value is not
available here, the rubric receives UNKNOWN and demotes. Numbers are never
invented downstream.
"""

from __future__ import annotations

import json
import os
from datetime import date

import requests

from engine.models import UNKNOWN
from engine.ports import BusinessState  # noqa: F401 (documents the fulfilled contract)
from integrations.tidepool import config, sharepoint_client as sp

# Known TIDEPOOL constants (sunk facts, safe to state, not live metrics).
DTC_PRICE = 24.99
B2B_LANDED_COST = 11.31

# Non-operating / one-time categories excluded from recurring burn. Copied from
# the finance agent's canonical opex calc (~/tidepool-finance-agent) so IDEA LOSS
# reports the SAME burn the rest of the OS does. Using the raw latest-month
# TotalDebits instead folds one-time inventory/lot and capital movements into
# burn and roughly halves runway (an artifact that makes the gate over-kill).
BURN_EXCLUDE_CATEGORIES = {
    "Internal Transfer", "Owner Draw", "Owner Reimbursement",
    "Capital Reimbursement", "Inventory",
}

# live_state.json drive item (Ops Agent). Overridable via env for a new workspace.
LIVE_STATE_URL = os.environ.get(
    "LIVE_STATE_URL",
    "https://graph.microsoft.com/v1.0/drives/"
    "b!5syyXAVfvUGgFhuFyMoEFLkPI2LXg71Oudeh0sTPzHqDLpOUO7P6QKEGYrAjFE-1"
    "/root:/Ops Agent/live_state.json:/content",
)


def _read_named_table(site_env: str, file_env: str, table_name: str) -> list[dict]:
    """Generic read of any OS table by env-var-named coordinates. Never raises."""
    site_id = (os.environ.get(site_env, "") or "").strip()
    file_id = (os.environ.get(file_env, "") or "").strip()
    if not (site_id and file_id and sp.has_creds()):
        return []
    try:
        base = f"{sp.GRAPH_ROOT}/sites/{site_id}/drive/items/{file_id}/workbook/tables/{table_name}"
        hr = requests.get(f"{base}/headerRowRange", headers=sp._headers(), timeout=15)
        if hr.status_code != 200:
            return []
        cols = [str(c).strip() for c in hr.json().get("values", [[]])[0]]
        rr = requests.get(f"{base}/rows?$top=500", headers=sp._headers(), timeout=20)
        if rr.status_code != 200:
            return []
        out = []
        for item in rr.json().get("value", []):
            for vals in item.get("values", []):
                padded = list(vals) + [""] * max(0, len(cols) - len(vals))
                out.append({c: padded[i] for i, c in enumerate(cols)})
        return out
    except Exception:
        return []


def _recurring_monthly_burn() -> float | None:
    """Canonical recurring OpEx burn: FinanceLog debit rows, EXCLUDING one-time /
    non-operating categories (inventory, capital, owner draws, transfers),
    averaged over the distinct months present. Mirrors the finance agent's
    opex_summary so runway is consistent OS-wide. Test rows excluded like the
    canonical reader. Returns None when FinanceLog is unavailable, so burn/runway
    stay UNKNOWN rather than falling back to an inflated raw-debits figure."""
    rows = _read_named_table("FINANCE_SITE_ID", "FINANCE_FILE_ID", "FinanceLog")
    if not rows:
        return None
    total = 0.0
    months: set[str] = set()
    for r in rows:
        if str(r.get("TestRecord", "") or "").strip().upper() == "TRUE":
            continue
        if str(r.get("Type", "") or "").strip().lower() != "debit":
            continue
        if str(r.get("Category", "Other") or "Other").strip() in BURN_EXCLUDE_CATEGORIES:
            continue
        try:
            total += abs(float(r.get("Amount", 0) or 0))
        except (TypeError, ValueError):
            continue
        d = str(r.get("Date", "") or "")
        if d and d.replace(".", "").isdigit():
            d = sp.excel_serial_to_str(d)
        if len(d) >= 7:
            months.add(d[:7])
    if not months:
        return None
    return round(total / len(months), 2)


def _parse_date(val) -> date | None:
    """Parse an as-of date. Accepts ISO (YYYY-MM-DD) or an Excel date serial
    (Graph returns date cells as serials). Returns None if unparseable; we never
    invent a date."""
    s = str(val or "").strip()
    if not s:
        return None
    if s.replace(".", "").isdigit():
        s = sp.excel_serial_to_str(s)  # serial -> ISO (or unchanged on failure)
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _finance_summary_cash() -> tuple[float, date | None] | None:
    """Cash from the most recent FinanceSummary EndingBalance (the canonical
    BlueVine operating-account statement). Returns (balance, as_of) where as_of is
    the statement's StatementMonth date, or None if unavailable."""
    fs = _read_named_table("FINANCE_SITE_ID", "FINANCE_SUMMARY_FILE_ID", "FinanceSummary")
    rows = [r for r in fs if str(r.get("EndingBalance", "")).strip() != ""]
    if not rows:
        return None

    def _sm(r):
        try:
            return int(float(str(r.get("StatementMonth", "") or "")))
        except Exception:
            return 0

    latest = sorted(rows, key=_sm, reverse=True)[0]
    try:
        bal = round(float(latest.get("EndingBalance", 0) or 0), 2)
    except (TypeError, ValueError):
        return None
    return (bal, _parse_date(latest.get("StatementMonth")))


def _current_cash_override() -> tuple[float, date] | None:
    """Founder-entered current cash from the CashState table (most recent
    AsOfDate). Uses only real entered values: a row must carry BOTH a numeric
    CurrentBalance and a parseable AsOfDate, else it is ignored (never invented)."""
    best: tuple[float, date] | None = None
    for r in sp.read_table(config.CASHSTATE_TABLE):
        raw = str(r.get("CurrentBalance", "") or "").strip()
        if not raw:
            continue
        try:
            bal = round(float(raw), 2)
        except ValueError:
            continue
        d = _parse_date(r.get("AsOfDate"))
        if d is None:
            continue
        if best is None or d > best[1]:
            best = (bal, d)
    return best


def _fetch_live_state() -> dict:
    if not sp.has_creds():
        return {}
    try:
        resp = requests.get(LIVE_STATE_URL, headers=sp._headers(), timeout=10)
        if resp.status_code != 200:
            return {}
        return json.loads(resp.content)
    except Exception:
        return {}


class TidepoolBusinessState:
    """BusinessState backed by FinanceSummary + live_state.json. Caches per run."""

    def __init__(self) -> None:
        self._metrics: dict | None = None
        self._live: dict | None = None

    def _live_state(self) -> dict:
        if self._live is None:
            self._live = _fetch_live_state()
        return self._live

    def metrics(self) -> dict:
        if self._metrics is not None:
            return self._metrics
        m: dict = {"dtc_price": DTC_PRICE, "b2b_landed_cost": B2B_LANDED_COST}

        # Cash = the MORE RECENT of the founder-entered current balance and the
        # latest FinanceSummary ending balance, by as-of date. Both are the same
        # single BlueVine operating account, so cash is always flagged
        # single-account; old values are flagged stale. We never extrapolate a
        # mid-month figure: only real entered values are used. The cash_* metadata
        # keys are non-numeric on purpose so they are not offered as ROI metrics.
        fin = _finance_summary_cash()          # (balance, as_of|None) or None
        ovr = _current_cash_override()         # (balance, as_of) or None
        candidates = []
        if fin is not None:
            candidates.append((fin[0], fin[1], "finance_summary"))
        if ovr is not None:
            candidates.append((ovr[0], ovr[1], "founder_override"))
        dated = [c for c in candidates if c[1] is not None]
        chosen = max(dated, key=lambda c: c[1]) if dated else (candidates[0] if candidates else None)
        if chosen is not None:
            m["cash_balance"] = chosen[0]
            m["cash_source"] = chosen[2]
            m["cash_single_account"] = True  # only BlueVine checking is tracked
            if chosen[1] is not None:
                m["cash_as_of"] = chosen[1].isoformat()
                m["cash_is_stale"] = (date.today() - chosen[1]).days > config.CASH_STALE_DAYS
            else:
                m["cash_as_of"] = UNKNOWN
                m["cash_is_stale"] = True

        # Recurring burn from FinanceLog the canonical way (NOT raw TotalDebits).
        burn = _recurring_monthly_burn()
        if burn is not None:
            m["monthly_burn"] = burn
            if burn > 0 and "cash_balance" in m:
                m["runway_months"] = round(m["cash_balance"] / burn, 2)

        # Inventory from live_state.json.
        live = self._live_state()
        inv = live.get("inventory", {})
        total = 0
        have_inv = False
        for key in ("blueberry_lemon", "cherry_lime", "peach_mango"):
            sku = inv.get(key, {})
            qty = sku.get("available_qty", sku.get("available"))
            if qty not in (None, ""):
                try:
                    total += int(float(qty))
                    have_inv = True
                except (TypeError, ValueError):
                    pass
        if have_inv:
            m["total_inventory_units"] = total

        # Pipeline from live_state.json pipeline_forecast. Expressed in BAGS (the
        # only form present). A dollar pipeline_value needs a B2B per-bag revenue
        # figure, and AOV needs Sales-Agent / Shopify order data; neither is here,
        # so ideas tied to those metrics stay UNKNOWN -> GRAY until wired (tracked
        # in STAGE1_BUILD1.md).
        pf = live.get("pipeline_forecast", {})
        if isinstance(pf, dict):
            for src, dst in (("total_expected_bags", "pipeline_expected_bags"),
                             ("high_confidence_bags", "pipeline_high_confidence_bags")):
                val = pf.get(src)
                if val not in (None, ""):
                    try:
                        m[dst] = round(float(val), 2)
                    except (TypeError, ValueError):
                        pass

        self._metrics = m
        return m

    def top_priorities(self) -> list[str]:
        live = self._live_state()
        for key in ("priorities", "top_priorities"):
            val = live.get(key)
            if isinstance(val, list) and val:
                return [str(v) for v in val][:3]
        return config.DEFAULT_PRIORITIES

    def metric_value(self, metric_name: str) -> str:
        val = self.metrics().get(metric_name)
        return UNKNOWN if val is None else str(val)
