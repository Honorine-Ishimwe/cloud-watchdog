from tools._azure import run_az, use_fixtures
from tools._fixtures import load_fixture


def get_disks(resource_group: str = "") -> list[dict] | dict:
    if use_fixtures():
        data = load_fixture("disks.json")
    else:
        args = ["disk", "list"]
        if resource_group:
            args += ["-g", resource_group]
        data = run_az(args)

    if isinstance(data, dict):
        return data

    disks = []
    for d in data:
        disks.append({
            "name": d.get("name"),
            "id": d.get("id"),
            "diskState": d.get("diskState"),
            "diskSizeGB": d.get("diskSizeGB"),
            "timeCreated": d.get("timeCreated"),
            "managedBy": d.get("managedBy"),
            "sku": (d.get("sku") or {}).get("name"),
        })
    return disks
