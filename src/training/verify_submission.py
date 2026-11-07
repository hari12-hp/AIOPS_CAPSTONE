"""Verify saved submission evidence without loading a model or starting containers."""
import argparse
import json
from pathlib import Path


def load_report(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read required evaluation report: {path}: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="reports/evaluation/qwen_v2_generation.json")
    args = parser.parse_args()
    report_path = Path(args.report)
    report = load_report(report_path)
    case_count = len(report.get("cases", []))
    accuracy = report.get("accuracy")
    threshold = report.get("minimum_accuracy")
    passed = report.get("status") == "accepted" and isinstance(accuracy, (int, float)) and isinstance(threshold, (int, float)) and accuracy >= threshold and case_count > 0
    summary = {
        "report": str(report_path),
        "model": report.get("model"),
        "resolved_revision": report.get("resolved_revision"),
        "cases": case_count,
        "accuracy": accuracy,
        "minimum_accuracy": threshold,
        "decision": report.get("status"),
        "verification": "pass" if passed else "fail",
    }
    print(json.dumps(summary, indent=2))
    if not passed:
        raise SystemExit("Submission quality gate failed; inspect the report above.")


if __name__ == "__main__":
    main()
