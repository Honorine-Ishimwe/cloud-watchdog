from tools._azure import run_az, use_fixtures
from tools._fixtures import load_fixture


def list_resources(resource_group: str = "") -> list[dict] | dict:
    if use_fixtures():
        data = load_fixture("resource_list.json")
    else:
        args = ["resource", "list"]
        if resource_group:
            args += ["-g", resource_group]
        data = run_az(args)

    if isinstance(data, dict):  # error returned by helper
        return data

    resources = []
    for r in data:
        resources.append({
            "name": r.get("name"),
            "id": r.get("id"),
            "type": r.get("type"),
            "location": r.get("location"),
            "createdTime": r.get("createdTime"),
            "managedBy": r.get("managedBy"),
            "sku": (r.get("sku") or {}).get("name"),
        })
    return resources
