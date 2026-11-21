from tools._azure import run_az, use_fixtures
from tools._fixtures import load_fixture


def get_vm_status(resource_group: str = "") -> list[dict] | dict:
    """Return each VM in a resource group (or subscription if omitted) with size and power state."""
    if use_fixtures():
        data = load_fixture("vms.json")
    else:
        args = ["vm", "list", "-d"]
        if resource_group:
            args += ["-g", resource_group]
        data = run_az(args)

    if isinstance(data, dict):
        return data

    vms = []
    for vm in data:
        size = vm.get("size") or (vm.get("hardwareProfile") or {}).get("vmSize")
        vms.append({
            "name": vm.get("name"),
            "id": vm.get("id"),
            "size": size,
            "powerState": vm.get("powerState"),
            "location": vm.get("location"),
            "createdTime": vm.get("createdTime") or vm.get("timeCreated"),
        })
    return vms
