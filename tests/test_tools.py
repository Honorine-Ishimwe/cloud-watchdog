import json
import subprocess
from types import SimpleNamespace

import pytest

import config
from agent.loop import TOOL_MAP, TOOLS, resolve_openai_credential, run_tool
from tools.get_advisor import get_advisor_recommendations
from tools.get_cost import get_cost
from tools.get_disks import get_disks
from tools.get_metrics import get_metrics
from tools.get_public_ips import get_public_ips
from tools.get_vm_status import get_vm_status
from tools.list_resources import list_resources

SUB_PREFIX = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-watchdog-test"


@pytest.fixture(autouse=True)
def fixture_mode(monkeypatch):
    monkeypatch.setattr(config, "USE_FIXTURES", True)
    monkeypatch.setattr(config, "FIXTURES_DIR", "")


def test_list_resources_returns_two_cards():
    result = list_resources("rg-watchdog-test")
    assert len(result) == 2
    assert result[0]["id"].endswith("disk-unattached-01")


def test_disk_is_unattached():
    disk = get_disks("rg-watchdog-test")[0]
    assert disk["diskState"] == "Unattached"


def test_public_ip_is_not_attached():
    ip = get_public_ips("rg-watchdog-test")[0]
    assert ip["ipConfiguration"] is None


def test_vm_status_returns_stopped_and_running_vms():
    vms = get_vm_status("rg-watchdog-test")
    assert len(vms) == 2
    by_name = {vm["name"]: vm for vm in vms}
    assert by_name["vm-stopped-01"]["powerState"] == "VM stopped"
    assert by_name["vm-stopped-01"]["size"] == "Standard_D2s_v3"
    assert by_name["vm-idle-01"]["powerState"] == "VM running"
    assert by_name["vm-idle-01"]["size"] == "Standard_B2s"


def test_metrics_for_running_and_stopped_vms():
    running_id = f"{SUB_PREFIX}/providers/Microsoft.Compute/virtualMachines/vm-idle-01"
    stopped_id = f"{SUB_PREFIX}/providers/Microsoft.Compute/virtualMachines/vm-stopped-01"

    running = get_metrics(running_id)
    assert len(running["daily"]) == 6
    assert running["daily"][0]["average"] == 1.1

    stopped = get_metrics(stopped_id)
    assert stopped["daily"] == []
    assert "stopped" in stopped["note"].lower()


def test_cost_returns_resource_costs():
    result = get_cost("rg-watchdog-test")
    assert len(result["costs"]) == 4
    assert result["costs"][0]["currency"] == "USD"
    assert "note" in result


def test_advisor_recommendations_returns_cost_rec():
    recs = get_advisor_recommendations("rg-watchdog-test")
    assert len(recs) == 1
    assert recs[0]["resource"] == "vm-idle-01"
    assert recs[0]["savingsCurrency"] == "USD"


def test_agent_registers_all_tools():
    schema_names = {t["function"]["name"] for t in TOOLS}
    assert schema_names == set(TOOL_MAP.keys())
    assert {
        "get_vm_status",
        "get_metrics",
        "get_cost",
        "get_advisor_recommendations",
    }.issubset(schema_names)


def test_run_tool_handles_valid_and_invalid_calls():
    vms = run_tool("get_vm_status", json.dumps({"resource_group": "rg-watchdog-test"}))
    assert isinstance(vms, list) and len(vms) == 2

    unknown = run_tool("does_not_exist", "{}")
    assert "error" in unknown

    bad_args = run_tool("get_vm_status", "not-json")
    assert "error" in bad_args


def test_az_cli_mode_vm_metrics_cost_and_advisor(monkeypatch):
    monkeypatch.setattr(config, "USE_FIXTURES", False)
    seen_cmds = []

    def fake_run(cmd, capture_output, text, timeout):
        seen_cmds.append(cmd)
        joined = " ".join(cmd)
        if "vm list" in joined:
            payload = [{
                "name": "vm-live-01",
                "id": "/subs/1/rg/live/vm-live-01",
                "powerState": "VM stopped",
                "location": "eastus",
                "timeCreated": "2026-10-01T00:00:00Z",
                "hardwareProfile": {"vmSize": "Standard_B1s"},
            }]
        elif "monitor metrics list" in joined:
            payload = {
                "value": [{
                    "timeseries": [{
                        "data": [
                            {"timeStamp": "2026-10-05T00:00:00Z", "average": 2.345, "maximum": 9.876},
                            {"timeStamp": "2026-10-06T00:00:00Z", "average": None, "maximum": None},
                        ]
                    }]
                }]
            }
        elif "advisor recommendation list" in joined:
            payload = [{
                "impactedValue": "vm-live-01",
                "impactedField": "Microsoft.Compute/virtualMachines",
                "impact": "High",
                "shortDescription": {"problem": "Idle VM", "solution": "Deallocate"},
                "extendedProperties": {"savingsAmount": "12.00", "savingsCurrency": "USD"},
            }]
        elif "account show" in joined:
            payload = {"id": "sub-123"}
        elif "rest" in joined:
            payload = {
                "properties": {
                    "columns": [
                        {"name": "PreTaxCost"},
                        {"name": "ResourceId"},
                        {"name": "Currency"},
                    ],
                    "rows": [[12.3456, "/subs/1/rg/live/vm-live-01", "USD"]],
                }
            }
        else:
            payload = []
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    vms = get_vm_status("")  # subscription-wide omits -g
    assert "-g" not in seen_cmds[-1]
    assert vms[0]["size"] == "Standard_B1s"

    metrics = get_metrics("/subs/1/rg/live/vm-live-01")
    assert metrics["daily"] == [{"date": "2026-10-05", "average": 2.35, "maximum": 9.88}]

    costs = get_cost("rg-live")
    assert costs["costs"] == [{"resource": "/subs/1/rg/live/vm-live-01", "cost": 12.3456, "currency": "USD"}]

    recs = get_advisor_recommendations("rg-live")
    assert recs[0]["resource"] == "vm-live-01"
    assert recs[0]["savingsAmount"] == "12.00"


def test_az_cli_errors_return_error_dict(monkeypatch):
    monkeypatch.setattr(config, "USE_FIXTURES", False)

    def missing_az(*args, **kwargs):
        raise FileNotFoundError("az")

    monkeypatch.setattr(subprocess, "run", missing_az)
    res = list_resources("rg-live")
    assert "error" in res and "not found" in res["error"].lower()

    def failing_az(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="Please run 'az login'")

    monkeypatch.setattr(subprocess, "run", failing_az)
    res = get_disks("rg-live")
    assert "error" in res and "az login" in res["error"]


def test_resolve_openai_credential_key_vault_and_managed_identity(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")
    monkeypatch.setattr(config, "KEY_VAULT_NAME", "my-vault")
    monkeypatch.setattr(config, "USE_MANAGED_IDENTITY", False)

    def fake_kv(cmd, capture_output, text, timeout):
        assert "keyvault" in cmd
        return SimpleNamespace(returncode=0, stdout=json.dumps({"value": "kv-secret-123"}), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_kv)
    cred, err = resolve_openai_credential()
    assert cred == "kv-secret-123" and err is None

    monkeypatch.setattr(config, "KEY_VAULT_NAME", "")
    monkeypatch.setattr(config, "USE_MANAGED_IDENTITY", True)

    def fake_token(cmd, capture_output, text, timeout):
        assert "get-access-token" in cmd
        return SimpleNamespace(returncode=0, stdout=json.dumps({"accessToken": "mi-token-456"}), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_token)
    cred, err = resolve_openai_credential()
    assert cred == "mi-token-456" and err is None
