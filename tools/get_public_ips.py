from tools._fixtures import load_fixture


def get_public_ips(resource_group: str) -> list[dict] | dict:
    data = load_fixture("public_ips.json")
    if isinstance(data, dict):
        return data

    ips = []
    for ip in data:
        ips.append({
            "name": ip.get("name"),
            "id": ip.get("id"),
            "ipAddress": ip.get("ipAddress"),
            "publicIPAllocationMethod": ip.get("publicIPAllocationMethod"),
            "sku": (ip.get("sku") or {}).get("name"),
            "ipConfiguration": ip.get("ipConfiguration"),
        })
    return ips
