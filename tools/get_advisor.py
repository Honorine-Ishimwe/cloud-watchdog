from tools._azure import run_az, use_fixtures
from tools._fixtures import load_fixture


def get_advisor_recommendations(resource_group: str = "") -> list[dict] | dict:
    """Return Azure Advisor Cost recommendations for a resource group (or subscription if omitted)."""
    if use_fixtures():
        data = load_fixture("advisor.json")
    else:
        args = ["advisor", "recommendation", "list", "--category", "Cost"]
        if resource_group:
            args += ["-g", resource_group]
        data = run_az(args)

    if isinstance(data, dict):
        return data

    recommendations = []
    for rec in data:
        props = rec.get("extendedProperties") or {}
        short_desc = rec.get("shortDescription") or {}
        recommendations.append({
            "resource": rec.get("impactedValue"),
            "resourceType": rec.get("impactedField"),
            "impact": rec.get("impact"),
            "problem": short_desc.get("problem"),
            "solution": short_desc.get("solution"),
            "annualSavingsAmount": props.get("annualSavingsAmount"),
            "savingsAmount": props.get("savingsAmount"),
            "savingsCurrency": props.get("savingsCurrency"),
        })
    return recommendations
