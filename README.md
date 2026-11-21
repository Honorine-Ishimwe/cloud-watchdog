# Cloud Cost Watchdog

An AI-powered, **read-only** Azure cloud cost auditor. It uses `gpt-4.1-mini` in a guardrailed tool-calling loop to inspect an Azure resource group (or entire subscription), gather concrete evidence from Azure Resource Manager, Monitor, Cost Management, and Advisor, and write a structured Markdown report of wasted spend.

## What It Detects (and Ignores)

| Category | Flagged as Waste | Ignored (Decoys / Healthy) |
|---|---|---|
| **Managed Disks** | `diskState == "Unattached"` and `managedBy` is empty | Attached disks (`diskState == "Attached"`) |
| **Public IPs** | Static Standard IP with `ipConfiguration == null` | Associated public IPs |
| **Virtual Machines (Power)** | `powerState == "VM stopped"` (still billed for compute) | `powerState == "VM deallocated"` |
| **Virtual Machines (CPU)** | Running VM with consistently very low CPU (`get_metrics`) | Busy running VMs |
| **Cost & Advisor Evidence** | Actual spend (`get_cost`) + Azure Advisor Cost recommendations (`get_advisor_recommendations`) | Missing/lagging data is reported honestly, never invented |

## Architecture & Guardrails

```
main.py (CLI: resource group / --subscription / --fixtures)
   │
   ▼
agent/loop.py (gpt-4.1-mini tool-calling loop, MAX_STEPS=12)
   ├── tools/list_resources.py          ──▶ az resource list  (or fixtures)
   ├── tools/get_disks.py               ──▶ az disk list
   ├── tools/get_public_ips.py          ──▶ az network public-ip list
   ├── tools/get_vm_status.py           ──▶ az vm list -d
   ├── tools/get_metrics.py             ──▶ az monitor metrics list
   ├── tools/get_cost.py                ──▶ az rest (Cost Management query)
   ├── tools/get_advisor.py             ──▶ az advisor recommendation list
   └── report/write_report.py           ──▶ reports/report-YYYY-MM-DD.md
```

- **Strictly read-only:** Every tool only reads metadata, metrics, costs, or recommendations — nothing modifies or deletes Azure resources.
- **Step limit:** `MAX_STEPS` (default `12`) caps the maximum number of model calls.
- **Errors as data:** `run_tool()` catches all exceptions and returns `{"error": "..."}` so the agent loop never crashes on bad arguments or API failures.
- **Evidence-grounded:** The prompt and report schema require quoting exact fields and values from tool outputs.

## Demo Output

See [docs/sample-report.md](docs/sample-report.md) for an example audit report generated from the evaluation scenario (4 planted waste items + 4 decoys).

## Quickstart

### 1. Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with your Azure OpenAI endpoint and API key:
```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
```

### 2. Run Offline with Fixtures
```bash
python main.py --fixtures
```

### 3. Run Live Against Azure
```bash
az login
python main.py rg-watchdog-test          # audit a single resource group
python main.py --subscription            # audit the entire subscription
```

## Testing & Accuracy Evaluation

### Unit Tests (offline, no Azure or OpenAI credentials needed)
```bash
pytest -v
```

### 3-Run Accuracy Evaluation (planted waste + decoys)
`eval/fixtures/` contains 4 planted waste items (`disk-unattached-01`, `pip-unused-01`, `vm-stopped-01`, `vm-idle-01`) and 4 decoys (`disk-attached-prod`, `pip-prod-web`, `vm-busy-prod`, `vm-deallocated-01`). Run the agent 3 times and score hits, misses, and false positives:

```bash
python eval/run_eval.py --runs 3
```

## Docker

```bash
docker build -t cloud-watchdog .

# Offline fixture run
docker run --rm --env-file .env cloud-watchdog --fixtures

# Live run (mounting local Azure CLI auth)
docker run --rm --env-file .env -v "$HOME/.azure:/home/watchdog/.azure:ro" cloud-watchdog rg-watchdog-test
```

## Deploying Scheduled Runs on Azure (Container Apps Job)

[deploy/container-app-job.bicep](deploy/container-app-job.bicep) deploys a daily scheduled **Azure Container Apps Job** with a **System-Assigned Managed Identity** (no static Azure credentials):

1. Build and push the image to Azure Container Registry.
2. Deploy `deploy/container-app-job.bicep` with your Container Apps Environment ID, image, and Azure OpenAI endpoint.
3. Grant the job's `principalId` read-only RBAC roles:
   - `Reader` and `Cost Management Reader` on the target resource group or subscription.
   - `Cognitive Services OpenAI User` on your Azure OpenAI resource (or `Key Vault Secrets User` if storing the API key in Key Vault via `AZURE_KEY_VAULT_NAME`).

## CI

[.github/workflows/ci.yml](.github/workflows/ci.yml) runs `pytest` and validates the `Dockerfile` build on every push and pull request to `main`.
