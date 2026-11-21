import json
from types import SimpleNamespace

import config
from agent.loop import run_agent_session
from eval.run_eval import EVAL_FIXTURES_DIR, score_findings
from report.write_report import write_report
from tools.get_disks import get_disks
from tools.get_vm_status import get_vm_status


def _make_tool_call(call_id: str, name: str, args: dict):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        msg = self._responses.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def test_write_report_with_findings_and_empty(tmp_path):
    out = tmp_path / "report.md"
    res = write_report(
        [{
            "resource": "disk-unattached-01",
            "problem": "Unattached disk",
            "evidence": "diskState=Unattached",
            "estimated_monthly_cost": 5.89,
            "suggested_action": "Delete disk",
            "confidence": "high",
        }],
        output_path=str(out),
    )
    assert res["path"] == str(out)
    text = out.read_text()
    assert "Total Estimated Monthly Waste:** $5.89 USD" in text
    assert "## 1. disk-unattached-01" in text

    empty_out = tmp_path / "empty.md"
    write_report([], output_path=str(empty_out))
    assert "No wasteful resources were found." in empty_out.read_text()


def test_run_agent_session_end_to_end_and_step_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "USE_FIXTURES", True)
    monkeypatch.setattr(config, "FIXTURES_DIR", "")

    out = tmp_path / "agent-report.md"
    fake_client = _FakeClient([
        SimpleNamespace(
            content=None,
            tool_calls=[_make_tool_call("c1", "list_resources", {"resource_group": "rg-watchdog-test"})],
        ),
        SimpleNamespace(
            content=None,
            tool_calls=[_make_tool_call("c2", "write_report", {
                "findings": [{
                    "resource": "disk-unattached-01",
                    "problem": "Unattached disk",
                    "evidence": "diskState=Unattached, managedBy=None",
                    "estimated_monthly_cost": 0.64,
                    "suggested_action": "Delete disk",
                    "confidence": "high",
                }],
            })],
        ),
    ])

    session = run_agent_session("rg-watchdog-test", output_path=str(out), client=fake_client, verbose=False)
    assert session["report_path"] == str(out)
    assert session["steps"] == 2
    assert len(session["findings"]) == 1
    assert out.exists()

    # Step limit guardrail
    monkeypatch.setattr(config, "MAX_STEPS", 2)
    looping_client = _FakeClient([
        SimpleNamespace(content=None, tool_calls=[_make_tool_call("c1", "list_resources", {})]),
        SimpleNamespace(content=None, tool_calls=[_make_tool_call("c2", "list_resources", {})]),
    ])
    stopped = run_agent_session("rg-watchdog-test", client=looping_client, verbose=False)
    assert stopped["report_path"] is None
    assert "step limit" in stopped["status"].lower()


def test_eval_scorer_and_decoy_fixtures(monkeypatch):
    expected = ["disk-unattached-01", "pip-unused-01", "vm-stopped-01", "vm-idle-01"]
    decoys = ["disk-attached-prod", "pip-prod-web", "vm-busy-prod", "vm-deallocated-01"]

    perfect = score_findings(
        [
            {"resource": "/subscriptions/0/resourceGroups/rg/providers/Microsoft.Compute/disks/disk-unattached-01"},
            {"resource": "pip-unused-01"},
            {"resource": "vm-stopped-01"},
            {"resource": "vm-idle-01"},
        ],
        expected,
        decoys,
    )
    assert perfect["precision"] == 1.0
    assert perfect["recall"] == 1.0
    assert perfect["misses"] == []
    assert perfect["false_positives"] == []

    noisy = score_findings(
        [{"resource": "disk-unattached-01"}, {"resource": "vm-busy-prod"}],
        expected,
        decoys,
    )
    assert noisy["hits"] == ["disk-unattached-01"]
    assert len(noisy["misses"]) == 3
    assert noisy["decoy_alarms"] == ["vm-busy-prod"]
    assert noisy["precision"] == 0.5
    assert noisy["recall"] == 0.25

    # Verify eval fixtures load cleanly and contain both waste and decoys
    monkeypatch.setattr(config, "USE_FIXTURES", True)
    monkeypatch.setattr(config, "FIXTURES_DIR", str(EVAL_FIXTURES_DIR))
    disks = get_disks("rg-watchdog-eval")
    assert {d["name"] for d in disks} == {"disk-unattached-01", "disk-attached-prod"}
    vms = get_vm_status("rg-watchdog-eval")
    assert {v["name"] for v in vms} == {"vm-stopped-01", "vm-idle-01", "vm-busy-prod", "vm-deallocated-01"}
