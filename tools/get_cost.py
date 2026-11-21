import json
from datetime import datetime, timedelta, timezone

from tools._azure import run_az, use_fixtures
from tools._fixtures import load_fixture

COST_LAG_NOTE = "Azure cost data can lag by up to 24 hours; newly created resources may not appear yet."


def _parse_cost_query(data: dict) -> list[dict]:
    props = data.get("properties") or {}
    columns = [c.get("name") for c in props.get("columns", [])]
    rows = props.get("rows", [])

    try:
        cost_idx = columns.index("PreTaxCost")
        res_idx = columns.index("ResourceId")
        cur_idx = columns.index("Currency")
    except ValueError:
        return []

    costs = []
    for row in rows:
        if len(row) <= max(cost_idx, res_idx, cur_idx):
            continue
        costs.append({
            "resource": row[res_idx],
            "cost": round(float(row[cost_idx]), 4),
            "currency": row[cur_idx],
        })
    return costs


def get_cost(resource_group: str = "", days: int = 30) -> dict:
    """Return what each resource in the group (or subscription if omitted) cost over the last `days` days."""
    if use_fixtures():
        data = load_fixture("costs.json")
        if not isinstance(data, dict) or "error" in data:
            return data if isinstance(data, dict) else {"error": "Unexpected costs fixture format."}

        costs = [
            {
                "resource": entry.get("resource"),
                "cost": entry.get("cost"),
                "currency": entry.get("currency"),
            }
            for entry in data.get("costs", [])
        ]
        note = data.get("note", "")
        if not costs and not note:
            note = COST_LAG_NOTE
        return {"costs": costs, "note": note}

    account = run_az(["account", "show"])
    if not isinstance(account, dict) or "error" in account:
        return account if isinstance(account, dict) else {"error": "Could not determine Azure subscription."}
    subscription_id = account.get("id")
    if not subscription_id:
        return {"error": "Active Azure subscription ID not found."}

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    body = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {
            "from": start.strftime("%Y-%m-%dT00:00:00Z"),
            "to": now.strftime("%Y-%m-%dT23:59:59Z"),
        },
        "dataset": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {"name": "PreTaxCost", "function": "Sum"},
            },
            "grouping": [
                {"type": "Dimension", "name": "ResourceId"},
            ],
        },
    }

    scope = f"/subscriptions/{subscription_id}"
    if resource_group:
        scope += f"/resourceGroups/{resource_group}"
    uri = f"https://management.azure.com{scope}/providers/Microsoft.CostManagement/query?api-version=2023-11-01"

    data = run_az(["rest", "--method", "post", "--uri", uri, "--body", json.dumps(body)])
    if not isinstance(data, dict):
        return {"error": "Unexpected response from Azure Cost Management."}
    if "error" in data:
        return data

    costs = _parse_cost_query(data)
    return {
        "costs": costs,
        "note": "" if costs else COST_LAG_NOTE,
    }
