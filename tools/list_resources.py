from tools._fixtures import load_fixture


def list_resources(resource_group: str) -> list[dict] | dict:
    data = load_fixture("resource_list.json")
    if isinstance(data, dict):  # an error came back from the helper
        return data

    resources = []
    for r in data:
        resources.append({
            "name": r.get("name"),
            "type": r.get("type"),
            "location": r.get("location"),
            "createdTime": r.get("createdTime"),
            "managedBy": r.get("managedBy"),
            "sku": (r.get("sku") or {}).get("name"),
        })
    return resources
