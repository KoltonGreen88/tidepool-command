"""
Reads live_state.json written by the Ops Agent.
Uses fetch_ops_live_state from the Finance Agent client pattern.
"""
from sharepoint.client import fetch_ops_live_state


def get_live_state() -> dict:
    result = fetch_ops_live_state()
    if result is None:
        return {
            "error": "live_state.json unavailable",
            "inventory": {},
            "suppress_new_commitments": False,
            "last_updated": None,
        }
    return result


def get_marketing_state() -> dict:
    """
    Fetch and parse marketing_state.json from the Marketing Agent.
    Same read pattern as live_state.json. TestRecord already filtered upstream.
    """
    import requests
    import json
    from sharepoint.client import _get_access_token, has_sharepoint_creds

    if not has_sharepoint_creds():
        return {"error": "no creds", "gifting": {}, "events": {}, "social": {}, "demand_signal": {}, "suppress_gifting": False}

    MKT_URL = (
        "https://graph.microsoft.com/v1.0/drives/"
        "b!FSnkmdVGHkqgGhYKcgYuLbkPI2LXg71Oudeh0sTPzHqDLpOUO7P6QKEGYrAjFE-1"
        "/root:/Marketing Agent/marketing_state.json:/content"
    )
    try:
        token = _get_access_token()
        resp = requests.get(MKT_URL, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if resp.status_code == 404:
            return {"error": "not found", "gifting": {}, "events": {}, "social": {}, "demand_signal": {}, "suppress_gifting": False}
        resp.raise_for_status()
        return json.loads(resp.content)
    except Exception as e:
        return {"error": str(e), "gifting": {}, "events": {}, "social": {}, "demand_signal": {}, "suppress_gifting": False}
