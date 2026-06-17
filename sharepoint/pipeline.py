"""
Reads SalesLeads from SharePoint using exact Sales Agent credentials and pattern.
"""
import os
import requests
from sharepoint.client import _get_access_token

SALES_DRIVE_ID = os.getenv("SALES_DRIVE_ID", "b!KnA__iPt-kigosnQX5gqVLkPI2LXg71Oudeh0sTPzHqDLpOUO7P6QKEGYrAjFE-1")
SALES_FILE_ID  = os.getenv("SALES_FILE_ID",  "01RSC2PJCYQ77XTEZMNFAJSBN6OXEJ3VR3")
TABLE_NAME     = "SalesLeads"

COLUMNS = [
    "id", "venue_name", "name", "stage", "owner", "category", "type", "visibility",
    "source", "address", "phone", "website", "email", "instagram", "contact_name",
    "notes", "additional_info", "next_action", "next_action_due", "last_contact",
    "outreach_draft", "outreach_medium", "created_at", "updated_at", "fit_score",
    "franchise_status",
]

STAGE_WEIGHTS = {
    "Active":      1.0,
    "In Progress": 0.6,
    "Warm Lead":   0.3,
    "Contacted":   0.1,
    "Prospect":    0.05,
}

WHOLESALE_BAGS = {
    "Active":      24,
    "In Progress": 18,
    "Warm Lead":   12,
    "Contacted":   12,
    "Prospect":    12,
}

STAGE_ORDER = ["Active", "In Progress", "Warm Lead", "Contacted", "Prospect"]

DEFAULT_PRICE_PER_BAG = 17.49


def _load_leads() -> list[dict]:
    try:
        token = _get_access_token()
        url = (
            f"https://graph.microsoft.com/v1.0/drives/{SALES_DRIVE_ID}"
            f"/items/{SALES_FILE_ID}/workbook/tables/{TABLE_NAME}/rows"
        )
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        resp.raise_for_status()
        rows = resp.json().get("value", [])
        result = []
        for row in rows:
            values = row.get("values", [[]])[0]
            # Exclude Test Mode records. TestRecord is appended after the known
            # COLUMNS; no base column holds the literal TRUE, and blank is FALSE.
            if any(str(v).strip().upper() == "TRUE" for v in values[len(COLUMNS):]):
                continue
            entry = {}
            for i, col in enumerate(COLUMNS):
                val = values[i] if i < len(values) else None
                entry[col] = val if val not in ("", None) else None
            if entry.get("id"):
                result.append(entry)
        return result
    except Exception:
        return []


def get_pipeline_data() -> dict:
    leads = _load_leads()

    if not leads:
        return {
            "total_weighted_value": 0.0,
            "active_count": 0,
            "in_progress_count": 0,
            "warm_lead_count": 0,
            "top_opportunity": "No leads loaded",
            "reorder_urgency": "unknown",
            "leads": [],
            "raw_leads": [],
            "source": "SalesLeads SharePoint",
        }

    total_weighted    = 0.0
    active_count      = 0
    in_progress_count = 0
    warm_lead_count   = 0
    top_opportunity   = None
    top_value         = 0.0
    enriched_leads    = []

    for lead in leads:
        stage      = lead.get("stage") or "Prospect"
        venue      = lead.get("venue_name") or lead.get("name") or "Unknown"
        fit_score  = float(lead.get("fit_score") or 5)
        franchise  = str(lead.get("franchise_status") or "").lower() == "franchise"
        weight     = STAGE_WEIGHTS.get(stage, 0.05)
        bags       = WHOLESALE_BAGS.get(stage, 12)
        fit_mult   = fit_score / 10.0
        franchise_mult = 0.7 if franchise else 1.0

        if stage == "Active":
            weighted_value = bags * DEFAULT_PRICE_PER_BAG
        else:
            weighted_value = bags * DEFAULT_PRICE_PER_BAG * weight * fit_mult * franchise_mult

        total_weighted += weighted_value

        if stage in ("Active", "In Progress"):
            active_count += 1
        if stage == "In Progress":
            in_progress_count += 1
        if stage == "Warm Lead":
            warm_lead_count += 1

        if stage != "Active" and weighted_value > top_value:
            top_value = weighted_value
            top_opportunity = f"{venue} ({stage}, fit {fit_score:.0f}/10, ~${weighted_value:,.0f})"

        enriched_leads.append({
            "id": lead.get("id"),
            "venue": venue,
            "stage": stage,
            "stage_order": STAGE_ORDER.index(stage) if stage in STAGE_ORDER else 99,
            "fit_score": fit_score,
            "franchise": franchise,
            "weighted_value": round(weighted_value, 2),
            "bags": bags,
            "category": lead.get("category") or "",
            "owner": lead.get("owner") or "",
            "contact": lead.get("contact_name") or "",
            "phone": lead.get("phone") or "",
            "email": lead.get("email") or "",
            "next_action": lead.get("next_action") or "",
            "next_action_due": lead.get("next_action_due") or "",
            "last_contact": lead.get("last_contact") or "",
            "notes": lead.get("notes") or "",
            "visibility": lead.get("visibility") or "",
            "outreach_draft": lead.get("outreach_draft") or "",
        })

    enriched_leads.sort(key=lambda x: (x["stage_order"], -x["weighted_value"]))

    if total_weighted > 180 * DEFAULT_PRICE_PER_BAG:
        reorder_urgency = "high"
    elif total_weighted > 90 * DEFAULT_PRICE_PER_BAG:
        reorder_urgency = "medium"
    else:
        reorder_urgency = "low"

    return {
        "total_weighted_value": round(total_weighted, 2),
        "active_count": active_count,
        "in_progress_count": in_progress_count,
        "warm_lead_count": warm_lead_count,
        "top_opportunity": top_opportunity or "No open opportunities",
        "reorder_urgency": reorder_urgency,
        "leads": enriched_leads,
        "source": "SalesLeads SharePoint",
    }
