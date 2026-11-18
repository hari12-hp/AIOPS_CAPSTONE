"""Validate acceptance evidence by recomputing every recorded case decision."""

import argparse
import json
import math
from pathlib import Path
import re


def validate_report(report: dict) -> dict:
    cases = report.get("cases", [])
    if not cases or len({c.get("id") for c in cases}) != len(cases):
        raise ValueError("Acceptance evidence needs nonempty, uniquely identified cases")
    decisions = []
    for case in cases:
        patterns = case.get("accepted_patterns", [])
        if not patterns or not isinstance(case.get("answer"), str):
            raise ValueError("Every case needs declared patterns and a raw answer")
        passed = any(re.search(pattern, case["answer"]) for pattern in patterns)
        if passed != case.get("passed"):
            raise ValueError("Saved case decision disagrees with its raw answer")
        decisions.append(passed)
    accuracy = sum(decisions) / len(decisions)
    threshold = report.get("minimum_accuracy")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < threshold <= 1
    ):
        raise ValueError("Acceptance threshold must be in (0, 1]")
    saved_accuracy = report.get("accuracy")
    if (
        not isinstance(saved_accuracy, (int, float))
        or not math.isfinite(saved_accuracy)
        or not math.isclose(saved_accuracy, accuracy)
    ):
        raise ValueError("Saved accuracy disagrees with case results")
    accepted = accuracy >= threshold
    if report.get("status") != ("accepted" if accepted else "needs_review"):
        raise ValueError("Saved acceptance status disagrees with recomputed accuracy")
    return {
        "cases": len(cases),
        "accuracy": accuracy,
        "minimum_accuracy": threshold,
        "accepted": accepted,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="reports/evaluation/qwen_v2_generation.json")
    args = parser.parse_args()
    try:
        report = json.loads(Path(args.report).read_text())
        summary = validate_report(report)
    except (OSError, ValueError, KeyError, TypeError, re.error) as exc:
        raise SystemExit(f"Invalid acceptance evidence: {exc}") from exc
    print(json.dumps({"report": args.report, **summary}, indent=2))
    if not summary["accepted"]:
        raise SystemExit("Submission quality gate failed")


if __name__ == "__main__":
    main()
