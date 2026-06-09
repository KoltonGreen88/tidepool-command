"""
Assembles the full data payload sent to Claude on every call.
Pulls fresh data from live_state.json, Finance tables, and SalesLeads.
Never cached — always current.
"""
from datetime import datetime, timezone
from sharepoint.client import read_excel_table, _get_creds, _excel_serial_to_str
from sharepoint.state import get_live_state
from sharepoint.pipeline import get_pipeline_data

EXCLUDE_CATEGORIES = {
    "Internal Transfer",
    "Owner Draw",
    "Owner Reimbursement",
    "Capital Reimbursement",
    "Inventory",
}


def safe_float(val, default=0.0) -> float:
    try:
        return float(val or default)
    except (TypeError, ValueError):
        return default


def safe_int(val, default=0) -> int:
    try:
        return int(float(val or default))
    except (TypeError, ValueError):
        return default


def get_finance_summary() -> dict:
    try:
        c = _get_creds()
        rows = read_excel_table(
            site_id    = c.get("FINANCE_SITE_ID", ""),
            file_id    = c.get("FINANCE_SUMMARY_FILE_ID", ""),
            table_name = "FinanceSummary",
        )
        if not rows:
            return {"balance": 0.0, "monthly_burn": 0.0, "runway_months": 0.0}

        def _sm_sort(r):
            try:
                return int(float(str(r.get("StatementMonth", "") or "")))
            except Exception:
                return 0

        sorted_rows = sorted(
            [r for r in rows if r.get("EndingBalance", "") != ""],
            key=_sm_sort,
            reverse=True,
        )
        if not sorted_rows:
            return {"balance": 0.0, "monthly_burn": 0.0, "runway_months": 0.0}

        latest = sorted_rows[0]
        cash = safe_float(latest.get("EndingBalance", 0))
        # Burn = TotalDebits from most recent statement month
        burn = safe_float(latest.get("TotalDebits", 0))
        runway = round(cash / burn, 2) if burn > 0 else 0.0
        return {
            "balance": cash,
            "monthly_burn": burn,
            "runway_months": runway,
            "source": "FinanceSummary",
        }
    except Exception as e:
        return {"error": str(e), "balance": 0.0, "monthly_burn": 0.0, "runway_months": 0.0}


def get_finance_log_summary() -> dict:
    try:
        c = _get_creds()
        rows = read_excel_table(
            site_id    = c.get("FINANCE_SITE_ID", ""),
            file_id    = c.get("FINANCE_FILE_ID", ""),
            table_name = "FinanceLog",
        )
        revenue = 0.0
        opex = 0.0
        production_cogs = 9531.45
        months = set()

        for row in rows:
            tx_type = str(row.get("Type", "") or "").strip().lower()
            cat = str(row.get("Category", "Other") or "Other").strip()
            amount = safe_float(row.get("Amount", 0))

            if tx_type == "credit":
                revenue += amount
            elif tx_type == "debit" and cat not in EXCLUDE_CATEGORIES:
                opex += abs(amount)
                d = str(row.get("Date", "") or "")
                if d and str(d).replace(".", "").isdigit():
                    d = _excel_serial_to_str(d)
                if len(d) >= 7:
                    months.add(d[:7])

        gifting_cogs = get_gifting_cogs()
        net = revenue - production_cogs - opex - gifting_cogs
        monthly_burn = round(opex / len(months), 2) if months else 0.0

        return {
            "net": round(net, 2),
            "revenue": round(revenue, 2),
            "production_cogs": production_cogs,
            "opex": round(opex, 2),
            "gifting_cogs": round(gifting_cogs, 2),
            "monthly_burn_computed": monthly_burn,
            "source": "Finance Agent live",
        }
    except Exception as e:
        return {
            "error": str(e),
            "net": 0.0,
            "revenue": 0.0,
            "production_cogs": 9531.45,
            "opex": 0.0,
            "gifting_cogs": 0.0,
        }


def get_gifting_cogs() -> float:
    try:
        c = _get_creds()
        rows = read_excel_table(
            site_id    = c.get("SHAREPOINT_SITE_ID", ""),
            file_id    = c.get("GIFTING_FILE_ID", ""),
            table_name = "GiftingLog",
        )
        total_bags = sum(safe_int(r.get("Bags", 0)) for r in rows if safe_int(r.get("Bags", 0)) > 0)
        return round(total_bags * 11.31, 2)
    except Exception:
        return 0.0


def get_gifting_summary() -> dict:
    try:
        c = _get_creds()
        rows = read_excel_table(
            site_id    = c.get("SHAREPOINT_SITE_ID", ""),
            file_id    = c.get("GIFTING_FILE_ID", ""),
            table_name = "GiftingLog",
        )
        total_bags = sum(safe_int(r.get("Bags", 0)) for r in rows if safe_int(r.get("Bags", 0)) > 0)
        total_cogs = round(total_bags * 11.31, 2)
        confirmed = sum(1 for r in rows if str(r.get("Status", "")).lower() == "confirmed")
        return {
            "total_bags_gifted": total_bags,
            "total_cogs": total_cogs,
            "confirmed_count": confirmed,
            "source": "GiftingLog SharePoint",
        }
    except Exception as e:
        return {"error": str(e), "total_bags_gifted": 0, "total_cogs": 0.0, "confirmed_count": 0}


def get_inventory_from_state(live_state: dict) -> dict:
    inv = live_state.get("inventory", {})
    skus = {}
    for key in ("blueberry_lemon", "cherry_lime", "peach_mango"):
        sku_data = inv.get(key, {})
        skus[key] = {
            "available": safe_int(sku_data.get("available_qty", sku_data.get("available", 0))),
            "velocity_30d": safe_float(sku_data.get("velocity_30d", sku_data.get("velocity", 0))),
            "days_remaining": safe_int(sku_data.get("days_remaining", 0)),
            "status": sku_data.get("status", "unknown"),
        }
    total = sum(s["available"] for s in skus.values())
    suppress = live_state.get("suppress_new_commitments", False)
    return {
        "suppress_new_commitments": suppress,
        "total_available": total,
        "source": "live_state.json",
        **skus,
    }


def assemble_data_context(conversation_history: list = None) -> dict:
    live_state = get_live_state()
    finance_summary = get_finance_summary()
    pnl = get_finance_log_summary()
    inventory = get_inventory_from_state(live_state)
    pipeline = get_pipeline_data()
    gifting = get_gifting_summary()

    # Prefer burn from FinanceSummary, fall back to computed from FinanceLog
    if finance_summary.get("monthly_burn", 0) == 0 and pnl.get("monthly_burn_computed", 0) > 0:
        finance_summary["monthly_burn"] = pnl["monthly_burn_computed"]
        if finance_summary.get("balance", 0) > 0:
            finance_summary["runway_months"] = round(
                finance_summary["balance"] / finance_summary["monthly_burn"], 2
            )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cash": finance_summary,
        "pnl": pnl,
        "inventory": inventory,
        "pipeline": pipeline,
        "gifting": gifting,
        "live_state_meta": {
            "last_updated": live_state.get("last_updated"),
            "ops_agent_status": "ok" if "error" not in live_state else "error",
        },
        "sales_placeholder": {
            "leads": pipeline.get("leads", []),
            "outreach_log": [],
            "commit_history": [],
        },
        "marketing_placeholder": {
            "creator_roster": [],
            "event_log": [],
            "content_performance": [],
            "demand_signal": {},
        },
        "conversation_history": conversation_history or [],
    }
