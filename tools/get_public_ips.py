from tools._azure import run_az, use_fixtures
from tools._fixtures import load_fixture


def get_public_ips(resource_group: str = "") -> list[dict] | dict:
    if use_fixtures():
        data = load_fixture("public_ips.json")
    else:
        args = ["network", "public-ip", "list"]
        if resource_group:
            args += ["-g", resource_group]
        data = run_az(args)

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
