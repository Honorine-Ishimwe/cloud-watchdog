import argparse

import config
from agent.loop import run_agent


def main():
    parser = argparse.ArgumentParser(description="Audit an Azure resource group or subscription for wasted spend.")
    parser.add_argument(
        "resource_group",
        nargs="?",
        default="rg-watchdog-test",
        help="Azure resource group name (default: rg-watchdog-test)",
    )
    parser.add_argument(
        "--subscription",
        action="store_true",
        help="Audit the entire active Azure subscription instead of a single resource group",
    )
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Read local JSON fixtures instead of calling Azure CLI",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Custom output path for the markdown report (default: reports/report-YYYY-MM-DD.md)",
    )
    args = parser.parse_args()

    if args.fixtures:
        config.USE_FIXTURES = True

    rg = "" if args.subscription else args.resource_group
    print(run_agent(resource_group=rg, output_path=args.output))


if __name__ == "__main__":
    main()
