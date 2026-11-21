from tools._azure import run_az, use_fixtures
from tools._fixtures import load_fixture

NO_DATA_NOTE = (
    "No metric data available for this period (the resource may be stopped/deallocated "
    "or not emit this metric). Do not interpret missing data as 0% usage."
)


def _extract_fixture_entry(data: dict, resource_id: str) -> dict:
    by_resource = data.get("by_resource")
    if isinstance(by_resource, dict):
        if resource_id in by_resource:
            return by_resource[resource_id]
        # Allow matching by resource name suffix if full ARM ID wasn't passed
        short_name = resource_id.rstrip("/").split("/")[-1]
        for key, value in by_resource.items():
            if key.rstrip("/").split("/")[-1] == short_name:
                return value
        return {"daily": [], "note": NO_DATA_NOTE}
    return data


def _parse_az_metrics(data: dict) -> list[dict]:
    daily = []
    for series_group in data.get("value", []):
        for ts in series_group.get("timeseries", []):
            for point in ts.get("data", []):
                avg = point.get("average")
                mx = point.get("maximum")
                if avg is None and mx is None:
                    continue
                timestamp = point.get("timeStamp") or ""
                daily.append({
                    "date": timestamp[:10],
                    "average": round(avg, 2) if isinstance(avg, (int, float)) else avg,
                    "maximum": round(mx, 2) if isinstance(mx, (int, float)) else mx,
                })
    return daily


def get_metrics(resource_id: str, metric: str = "Percentage CPU", days: int = 7) -> dict:
    """Return daily average/maximum metric values for a resource over the last `days` days."""
    if use_fixtures():
        data = load_fixture("metrics.json")
        if not isinstance(data, dict) or "error" in data:
            return data if isinstance(data, dict) else {"error": "Unexpected metrics fixture format."}

        entry = _extract_fixture_entry(data, resource_id)
        daily_metrics = [
            {
                "date": point.get("date"),
                "average": point.get("average"),
                "maximum": point.get("maximum"),
            }
            for point in entry.get("daily", [])
        ]
        note = entry.get("note", "")
        if not daily_metrics and not note:
            note = NO_DATA_NOTE

        return {
            "resource_id": resource_id,
            "metric": metric,
            "daily": daily_metrics,
            "note": note,
        }

    data = run_az([
        "monitor", "metrics", "list",
        "--resource", resource_id,
        "--metric", metric,
        "--interval", "P1D",
        "--aggregation", "Average", "Maximum",
        "--offset", f"{days}d",
    ])
    if not isinstance(data, dict):
        return {"error": "Unexpected response from Azure Monitor metrics."}
    if "error" in data:
        return data

    daily_metrics = _parse_az_metrics(data)
    return {
        "resource_id": resource_id,
        "metric": metric,
        "daily": daily_metrics,
        "note": "" if daily_metrics else NO_DATA_NOTE,
    }
