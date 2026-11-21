# Cloud Cost Watchdog Report

- **Date:** 2026-10-13
- **Findings:** 4
- **Total Estimated Monthly Waste:** $109.99 USD

## 1. disk-unattached-01

- **Problem:** Unattached managed disk incurring ongoing storage charges.
- **Evidence:** `diskState` is `"Unattached"`, `managedBy` is `null`, `diskSizeGB` is `128`, `sku` is `"Standard_LRS"`; `get_cost` reports `$5.89 USD`.
- **Estimated monthly cost:** $5.89 USD
- **Suggested action:** Snapshot if needed for retention, then delete the unattached disk `disk-unattached-01`.
- **Confidence:** high

## 2. pip-unused-01

- **Problem:** Unused Standard Static public IP address billed while unassociated.
- **Evidence:** `ipConfiguration` is `null`, `publicIPAllocationMethod` is `"Static"`, `sku` is `"Standard"`, `ipAddress` is `"20.10.20.30"`; `get_cost` reports `$3.65 USD`.
- **Estimated monthly cost:** $3.65 USD
- **Suggested action:** Release and delete the unused public IP `pip-unused-01`.
- **Confidence:** high

## 3. vm-stopped-01

- **Problem:** Virtual machine is stopped in the OS but not deallocated, so compute billing continues.
- **Evidence:** `powerState` is `"VM stopped"` (not `"VM deallocated"`), `size` is `"Standard_D2s_v3"`; `get_cost` reports `$70.08 USD`.
- **Estimated monthly cost:** $70.08 USD
- **Suggested action:** Deallocate `vm-stopped-01` (`az vm deallocate`) to stop compute billing, or delete if no longer needed.
- **Confidence:** high

## 4. vm-idle-01

- **Problem:** Running virtual machine with consistently idle CPU utilization.
- **Evidence:** `powerState` is `"VM running"`, `size` is `"Standard_B2s"`; `get_metrics` shows daily `Percentage CPU` averaging `0.8%–1.2%` (max `2.4%–3.8%`) over 5 days; Azure Advisor Cost recommendation flags underutilization (`$30.37 USD/month`); `get_cost` reports `$30.37 USD`.
- **Estimated monthly cost:** $30.37 USD
- **Suggested action:** Right-size to a smaller SKU or schedule auto-shutdown / deallocate `vm-idle-01`.
- **Confidence:** high
