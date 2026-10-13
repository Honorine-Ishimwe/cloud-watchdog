import json
from pathlib import Path

def get_cost(resource_group: str, days: int = 30) -> list[dict] | dict:
    # Returns what each resource in the group cost over the last `days` days,
    # as a list of {"resource", "cost", "currency"}.
    # Fake version: reads tests/fixtures/costs.json (to be captured from real data).
    # Azure cost data lags by up to a day, so brand-new resources may show nothing;
    # when that happens, return what exists plus a "note" saying so.
    # On a missing file or invalid JSON, return {"error": "<message>"}.

    try:
        # Read the JSON file
        file_path = Path(__file__).parent / "tests" / "fixtures" / "costs.json"
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Process the costs
        costs = []
        for entry in data.get("costs", []):
            costs.append({
                "resource": entry.get("resource"),
                "cost": entry.get("cost"),
                "currency": entry.get("currency")
            })

        return {
            "costs": costs,
            "note": data.get("note", "")
        }
    except FileNotFoundError:
        return {"error": "File not found: costs.json"}
    except json.JSONDecodeError:    
        return {"error": "Invalid JSON in costs.json"}  