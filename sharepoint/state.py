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
