import json
from pathlib import Path

def get_vm_status(resource_group: str) -> list[dict] | dict:
    # Returns each VM in a resource group with its size and power state,
    # as a list of trimmed dictionaries.
    # Keep only: name, id, size, powerState, location, createdTime.
    # powerState tells us whether it is running, stopped, or deallocated;
    # a stopped-but-not-deallocated VM still costs money.
    # Fake version: reads tests/fixtures/vms.json (to be captured when we plant a VM).
    # On a missing file or invalid JSON, return {"error": "<message>"}.


    try:
        # Read the JSON file
        file_path = Path(__file__).parent / "tests" / "fixtures" / "vms.json"
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Process the VMs
        vms = []
        for vm in data:
            trimmed_vm = {
                "name": vm.get("name"),
                "id": vm.get("id"),
                "size": vm.get("size"),
                "powerState": vm.get("powerState"),
                "location": vm.get("location"),
                "createdTime": vm.get("createdTime")
            }
            vms.append(trimmed_vm)

        return vms
    except FileNotFoundError:
        return {"error": "File not found: vms.json"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in vms.json"}