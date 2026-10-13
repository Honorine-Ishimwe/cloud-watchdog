import json
from pathlib import Path

def write_report(findings: list[dict]) -> dict:
    # Saves the final findings as a markdown report and returns {"path": "<file path>"}.
    # Each finding has: resource, problem, evidence, estimated_monthly_cost,
    # suggested_action, and confidence.
    # Write to reports/report-YYYY-MM-DD.md (create the reports folder if it does not exist).
    # The report starts with a short summary (how many findings, total estimated monthly
    # waste), then one section per finding showing the evidence.
    # If the findings list is empty, still write a report that says nothing wasteful was found.
    # If the file cannot be written, return {"error": "<message>"}.
    # Calling this tool ends the agent loop.   


    try:
        # Create the reports directory if it does not exist
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)

        # Create the report file path
        report_file_path = reports_dir / f"report-{Path().resolve().name}.md"

        # Calculate total estimated monthly cost
        total_cost = sum(finding.get("estimated_monthly_cost", 0) for finding in findings)

        # Write the report
        with open(report_file_path, 'w') as report_file:
            # Write summary
            report_file.write(f"# Report - {len(findings)} Findings\n")
            report_file.write(f"Total Estimated Monthly Waste: ${total_cost:.2f}\n\n")

            # Write each finding
            for finding in findings:
                report_file.write(f"## Resource: {finding.get('resource')}\n")
                report_file.write(f"**Problem:** {finding.get('problem')}\n")
                report_file.write(f"**Evidence:** {finding.get('evidence')}\n")
                report_file.write(f"**Estimated Monthly Cost:** ${finding.get('estimated_monthly_cost', 0):.2f}\n")
                report_file.write(f"**Suggested Action:** {finding.get('suggested_action')}\n")
                report_file.write(f"**Confidence:** {finding.get('confidence')}\n\n")

        return {"path": str(report_file_path)}
    except Exception as e:
        return {"error": str(e)}    

