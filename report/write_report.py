from datetime import date
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def write_report(findings: list[dict], output_path: str | None = None) -> dict:
    """Save findings as a markdown file. Returns {"path": ...} or {"error": ...}."""
    try:
        today = date.today().isoformat()
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            REPORTS_DIR.mkdir(exist_ok=True)
            path = REPORTS_DIR / f"report-{today}.md"

        costs = [
            float(f["estimated_monthly_cost"])
            for f in findings
            if isinstance(f.get("estimated_monthly_cost"), (int, float))
        ]

        lines = [
            "# Cloud Cost Watchdog Report",
            "",
            f"- **Date:** {today}",
            f"- **Findings:** {len(findings)}",
        ]
        if costs:
            lines.append(f"- **Total Estimated Monthly Waste:** ${sum(costs):.2f} USD")
        lines.append("")

        if not findings:
            lines.append("No wasteful resources were found.")
        for i, f in enumerate(findings, start=1):
            lines += [
                f"## {i}. {f.get('resource', 'unknown resource')}",
                "",
                f"- **Problem:** {f.get('problem', '')}",
                f"- **Evidence:** {f.get('evidence', '')}",
            ]
            if isinstance(f.get("estimated_monthly_cost"), (int, float)):
                lines.append(f"- **Estimated monthly cost:** ${float(f['estimated_monthly_cost']):.2f} USD")
            lines += [
                f"- **Suggested action:** {f.get('suggested_action', '')}",
                f"- **Confidence:** {f.get('confidence', '')}",
                "",
            ]
        path.write_text("\n".join(lines))
        return {"path": str(path)}
    except OSError as e:
        return {"error": f"Could not write report: {e}"}
