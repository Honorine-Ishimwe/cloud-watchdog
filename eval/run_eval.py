import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from agent.loop import run_agent_session

EVAL_DIR = Path(__file__).parent
GROUND_TRUTH_PATH = EVAL_DIR / "ground_truth.json"
EVAL_FIXTURES_DIR = EVAL_DIR / "fixtures"


def _normalize_resource_name(name: str) -> str:
    """Extract the trailing resource name if a full ARM ID was returned."""
    return name.strip().rstrip("/").split("/")[-1].lower()


def score_findings(findings: list[dict], expected_waste: list[str], decoys: list[str]) -> dict:
    """Compare reported findings against expected waste and decoys."""
    expected_map = {n.lower(): n for n in expected_waste}
    decoy_map = {n.lower(): n for n in decoys}

    reported_norm = {_normalize_resource_name(f.get("resource", "")) for f in findings if f.get("resource")}

    hits = sorted(expected_map[n] for n in reported_norm if n in expected_map)
    misses = sorted(expected_map[n] for n in expected_map if n not in reported_norm)
    false_positives = sorted(
        decoy_map.get(n, n) for n in reported_norm if n not in expected_map
    )
    decoy_alarms = sorted(decoy_map[n] for n in reported_norm if n in decoy_map)

    precision = len(hits) / len(reported_norm) if reported_norm else (1.0 if not expected_waste else 0.0)
    recall = len(hits) / len(expected_waste) if expected_waste else 1.0

    return {
        "hits": hits,
        "misses": misses,
        "false_positives": false_positives,
        "decoy_alarms": decoy_alarms,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
    }


def run_evaluation(runs: int = 3) -> list[dict]:
    ground_truth = json.loads(GROUND_TRUTH_PATH.read_text())
    rg = ground_truth["resource_group"]
    expected_waste = ground_truth["expected_waste"]
    decoys = ground_truth["decoys"]

    config.USE_FIXTURES = True
    config.FIXTURES_DIR = str(EVAL_FIXTURES_DIR)

    results = []
    for run_idx in range(1, runs + 1):
        out_path = str(EVAL_DIR / "outputs" / f"eval-run-{run_idx}.md")
        session = run_agent_session(resource_group=rg, output_path=out_path, verbose=False)
        if session["report_path"] is None:
            print(f"[run {run_idx}/{runs}] FAILED: {session['status']}")
            results.append({"run": run_idx, "error": session["status"]})
            continue

        score = score_findings(session["findings"], expected_waste, decoys)
        score["run"] = run_idx
        score["steps"] = session["steps"]
        results.append(score)
        print(
            f"[run {run_idx}/{runs}] steps={session['steps']} "
            f"hits={len(score['hits'])}/{len(expected_waste)} "
            f"misses={score['misses']} "
            f"false_positives={score['false_positives']} "
            f"precision={score['precision']:.2f} recall={score['recall']:.2f}"
        )

    valid = [r for r in results if "error" not in r]
    if valid:
        avg_p = sum(r["precision"] for r in valid) / len(valid)
        avg_r = sum(r["recall"] for r in valid) / len(valid)
        print(f"\nSummary ({len(valid)}/{runs} completed): avg_precision={avg_p:.2f}, avg_recall={avg_r:.2f}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Run multi-trial accuracy evaluation with planted waste and decoys.")
    parser.add_argument("--runs", type=int, default=3, help="Number of evaluation runs (default: 3)")
    args = parser.parse_args()
    run_evaluation(runs=args.runs)


if __name__ == "__main__":
    main()
