import json
from pathlib import Path

def get_metrics(resource_id: str, metric: str = "Percentage CPU", days: int = 7) -> dict:
    # Returns how busy a resource was over the last `days` days,
    # as {"resource_id", "metric", "daily": [{"date", "average", "maximum"}]}.
    # Fake version: reads tests/fixtures/metrics.json (to be captured from a real VM).
    # If there is no data (for example, a stopped VM), return an empty "daily" list
    # plus a "note" explaining why. That is not an error, and it must not be
    # confused with 0% usage.
    # On a missing file or invalid JSON, return {"error": "<message>"}.


    try:
        # Read the JSON file
        file_path = Path(__file__).parent / "tests" / "fixtures" / "metrics.json"
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Process the metrics
        daily_metrics = []
        for entry in data.get("daily", []):
            daily_metrics.append({
                "date": entry.get("date"),
                "average": entry.get("average"),
                "maximum": entry.get("maximum")
            })

        return {
            "resource_id": resource_id,
            "metric": metric,
            "daily": daily_metrics,
            "note": data.get("note", "")
        }
    except FileNotFoundError:
        return {"error": "File not found: metrics.json"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in metrics.json"}    