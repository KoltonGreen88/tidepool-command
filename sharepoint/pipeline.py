"""
Reads SalesLeads from SharePoint and computes weighted pipeline metrics.
Uses read_excel_table from Finance Agent client pattern exclusively.
"""
from sharepoint.client import read_excel_table, _get_creds

SALES_TABLE_NAME = "SalesLeads"

STAGE_WEIGHTS = {
    "Closed Won": 1.0,
    "In Progress": 0.6,
    "Warm Lead": 0.3,
    "Cold Lead": 0.1,
    "Dead": 0.0,
}

DEFAULT_PRICE_PER_BAG = 17.49


def get_pipeline_data() -> dict:
    try:
        c = _get_creds()
        rows = read_excel_table(
            site_id    = c.get("FINANCE_SITE_ID", ""),
            file_id    = c.get("SALES_FILE_ID", ""),
            table_name = SALES_TABLE_NAME,
        )
    except Exception as e:
        return {
            "error": str(e),
            "total_weighted_value": 0.0,
            "active_count": 0,
            "in_progress_count": 0,
            "warm_lead_count": 0,
            "top_opportunity": "N/A",
            "reorder_urgency": "unknown",
            "leads": [],
        }

    total_weighted = 0.0
    active_count = 0
    in_progress_count = 0
    warm_lead_count = 0
    top_opportunity = None
    top_opportunity_value = 0.0
    leads = []

    for row in rows:
        stage = row.get("Stage", "Cold Lead")
        venue = row.get("VenueName", row.get("Venue", "Unknown"))
        expected_bags = float(row.get("ExpectedBags", row.get("Bags", 0)) or 0)
        price_per_bag = float(row.get("PricePerBag", DEFAULT_PRICE_PER_BAG) or DEFAULT_PRICE_PER_BAG)

        weight = STAGE_WEIGHTS.get(stage, 0.1)
        deal_value = expected_bags * price_per_bag
        weighted_value = deal_value * weight

        total_weighted += weighted_value

        if stage not in ("Dead", "Closed Won"):
            active_count += 1
        if stage == "In Progress":
            in_progress_count += 1
        if stage == "Warm Lead":
            warm_lead_count += 1

        if weighted_value > top_opportunity_value and stage != "Dead":
            top_opportunity_value = weighted_value
            top_opportunity = f"{venue} (~${weighted_value:,.0f} weighted)"

        leads.append({
            "venue": venue,
            "stage": stage,
            "expected_bags": expected_bags,
            "price_per_bag": price_per_bag,
            "deal_value": deal_value,
            "weighted_value": weighted_value,
            "weight": weight,
            "contact": row.get("ContactName", row.get("Contact", "")),
            "notes": row.get("Notes", ""),
        })

    leads.sort(key=lambda x: x["weighted_value"], reverse=True)

    if total_weighted > 3000:
        reorder_urgency = "high — pipeline demand warrants reorder soon"
    elif total_weighted > 1000:
        reorder_urgency = "moderate — monitor closely"
    else:
        reorder_urgency = "low"

    return {
        "total_weighted_value": round(total_weighted, 2),
        "active_count": active_count,
        "in_progress_count": in_progress_count,
        "warm_lead_count": warm_lead_count,
        "top_opportunity": top_opportunity or "No active leads",
        "reorder_urgency": reorder_urgency,
        "leads": leads,
    }
