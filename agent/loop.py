import json

from openai import OpenAI

import config
from report.write_report import write_report
from tools._azure import get_key_vault_secret, get_openai_auth_token
from tools.get_advisor import get_advisor_recommendations
from tools.get_cost import get_cost
from tools.get_disks import get_disks
from tools.get_metrics import get_metrics
from tools.get_public_ips import get_public_ips
from tools.get_vm_status import get_vm_status
from tools.list_resources import list_resources

SYSTEM_PROMPT = """You are Cloud Cost Watchdog, a read-only auditor of Azure cloud spend.
Your job: find wasted spend and explain every finding with concrete evidence.

What counts as waste:
- Unattached disk: diskState is "Unattached" (and managedBy is empty). It is billed by size while it exists.
- Unused public IP: no ipConfiguration, and publicIPAllocationMethod is "Static". Standard static IPs are billed even when unused.
- Stopped-but-not-deallocated VM: powerState is "VM stopped" (not "VM deallocated"). Compute is still billed while stopped.
- Idle running VM: powerState is "VM running" with consistently very low CPU usage over the checked period (e.g., daily average < 5% and maximum < 15%). Note: an empty "daily" metrics list with a "note" means data is missing (e.g., stopped VM), NOT 0% usage.

What is NOT waste (avoid false alarms):
- Attached disks (diskState is "Attached" or managedBy is set).
- Associated public IPs (ipConfiguration is present).
- Deallocated VMs (powerState is "VM deallocated").
- Busy/healthy running VMs (active CPU usage).

How to work:
1. Call list_resources first to see what exists.
2. Call get_disks, get_public_ips, and get_vm_status to inspect resource details.
3. For every running VM, call get_metrics with its resource id to check CPU utilization.
4. Call get_cost and get_advisor_recommendations to gather real spend numbers and Advisor evidence.
5. Only report what the tool results show. Never invent prices, sizes, or resources. If cost data is missing or lagging, say so.
6. When you have finished checking all resources, call write_report exactly once with one finding per wasteful resource (using its resource name). If nothing is wasteful, call it with an empty findings list.
"""

RG_PARAM = {
    "type": "object",
    "properties": {
        "resource_group": {
            "type": "string",
            "description": "Resource group name, or empty string to audit the entire subscription",
        }
    },
    "required": [],
}

TOOLS = [
    {"type": "function", "function": {
        "name": "list_resources",
        "description": "List every resource in the resource group or subscription (name, id, type, location, createdTime, managedBy, sku).",
        "parameters": RG_PARAM}},
    {"type": "function", "function": {
        "name": "get_disks",
        "description": "Get detailed info about disks, including diskState, diskSizeGB, and managedBy.",
        "parameters": RG_PARAM}},
    {"type": "function", "function": {
        "name": "get_public_ips",
        "description": "Get detailed info about public IP addresses, including ipConfiguration and publicIPAllocationMethod.",
        "parameters": RG_PARAM}},
    {"type": "function", "function": {
        "name": "get_vm_status",
        "description": "Get each VM with its size, powerState (running, stopped, or deallocated), location, and createdTime.",
        "parameters": RG_PARAM}},
    {"type": "function", "function": {
        "name": "get_metrics",
        "description": "Get daily average and maximum Azure Monitor metrics (default: Percentage CPU) for a resource over the last N days.",
        "parameters": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string", "description": "Full Azure resource ID"},
                "metric": {"type": "string", "description": "Metric name (default: Percentage CPU)"},
                "days": {"type": "integer", "description": "Number of days to look back (default: 7)"},
            },
            "required": ["resource_id"],
        }}},
    {"type": "function", "function": {
        "name": "get_cost",
        "description": "Get actual cost per resource over the last N days.",
        "parameters": {
            "type": "object",
            "properties": {
                "resource_group": {"type": "string", "description": "Resource group name, or empty string for subscription"},
                "days": {"type": "integer", "description": "Number of days to look back (default: 30)"},
            },
            "required": [],
        }}},
    {"type": "function", "function": {
        "name": "get_advisor_recommendations",
        "description": "Get Azure Advisor Cost recommendations as extra evidence.",
        "parameters": RG_PARAM}},
    {"type": "function", "function": {
        "name": "write_report",
        "description": "Save the final findings as a markdown report. Call this exactly once, at the end.",
        "parameters": {
            "type": "object",
            "properties": {"findings": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "resource": {"type": "string"},
                    "problem": {"type": "string"},
                    "evidence": {"type": "string", "description": "Quote the exact fields and values from the tool results"},
                    "estimated_monthly_cost": {"type": "number", "description": "Optional actual/estimated monthly cost in USD from get_cost or Advisor"},
                    "suggested_action": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["resource", "problem", "evidence", "suggested_action", "confidence"],
            }}},
            "required": ["findings"],
        }}},
]

TOOL_MAP = {
    "list_resources": list_resources,
    "get_disks": get_disks,
    "get_public_ips": get_public_ips,
    "get_vm_status": get_vm_status,
    "get_metrics": get_metrics,
    "get_cost": get_cost,
    "get_advisor_recommendations": get_advisor_recommendations,
    "write_report": write_report,
}


def resolve_openai_credential() -> tuple[str | None, str | None]:
    """Resolve Azure OpenAI auth: API key, Key Vault secret, or Managed Identity bearer token."""
    if config.API_KEY:
        return config.API_KEY, None
    if config.KEY_VAULT_NAME:
        return get_key_vault_secret(config.KEY_VAULT_NAME, config.KEY_VAULT_SECRET_NAME)
    if config.USE_MANAGED_IDENTITY:
        return get_openai_auth_token()
    return None, "Missing AZURE_OPENAI_API_KEY (or set AZURE_KEY_VAULT_NAME / AZURE_USE_MANAGED_IDENTITY=true)."


def run_tool(name: str, raw_args: str, output_path: str | None = None):
    """Run one tool the model asked for. Errors are returned as data, never raised."""
    func = TOOL_MAP.get(name)
    if func is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        args = json.loads(raw_args or "{}")
        if name == "write_report" and output_path:
            args["output_path"] = output_path
        return func(**args)
    except Exception as e:  # a bad call from the model must not crash the loop
        return {"error": f"Tool {name} failed: {e}"}


def run_agent_session(
    resource_group: str = "",
    output_path: str | None = None,
    client: OpenAI | None = None,
    verbose: bool = True,
) -> dict:
    """Run the watchdog loop and return {"status", "report_path", "findings", "steps"}."""
    if client is None:
        if not config.ENDPOINT:
            return {"status": "Missing AZURE_OPENAI_ENDPOINT in .env", "report_path": None, "findings": [], "steps": 0}
        credential, err = resolve_openai_credential()
        if err or not credential:
            return {"status": err or "Missing Azure OpenAI credentials.", "report_path": None, "findings": [], "steps": 0}
        client = OpenAI(
            base_url=config.ENDPOINT.rstrip("/") + "/openai/v1/",
            api_key=credential,
        )

    scope_desc = f"resource group '{resource_group}'" if resource_group else "entire Azure subscription"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Audit the {scope_desc} for wasted spend."},
    ]

    for step in range(1, config.MAX_STEPS + 1):
        response = client.chat.completions.create(
            model=config.DEPLOYMENT,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return {
                "status": message.content or "Agent stopped without a report.",
                "report_path": None,
                "findings": [],
                "steps": step,
            }

        report_path = None
        submitted_findings = []
        for call in message.tool_calls:
            name = call.function.name
            result = run_tool(name, call.function.arguments, output_path=output_path)
            if verbose:
                print(f"[step {step}] {name} -> {str(result)[:100]}")
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })
            if name == "write_report" and isinstance(result, dict) and "path" in result:
                report_path = result["path"]
                try:
                    submitted_findings = json.loads(call.function.arguments or "{}").get("findings", [])
                except json.JSONDecodeError:
                    submitted_findings = []

        if report_path:
            return {
                "status": f"Report written to {report_path}",
                "report_path": report_path,
                "findings": submitted_findings,
                "steps": step,
            }

    return {
        "status": "Stopped: step limit reached without a report.",
        "report_path": None,
        "findings": [],
        "steps": config.MAX_STEPS,
    }


def run_agent(resource_group: str = "", output_path: str | None = None) -> str:
    return run_agent_session(resource_group=resource_group, output_path=output_path)["status"]
