"""Move the local champion only when report and registered artifact identity agree."""

import argparse
import json
from pathlib import Path

from src.training.verify_submission import validate_report


def main():
    parser = argparse.ArgumentParser()
    for name in ("name", "version", "run-id", "evaluation"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    report = json.loads(Path(args.evaluation).read_text())
    decision = validate_report(report)
    if not decision["accepted"]:
        raise SystemExit("Refusing promotion: generated-answer acceptance failed")
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(f"sqlite:///{Path.cwd() / 'mlflow.db'}")
    client = MlflowClient()
    version = client.get_model_version(args.name, args.version)
    if version.run_id != args.run_id:
        raise SystemExit("The version belongs to another MLflow run")
    if (
        not report.get("adapter_sha256")
        or version.tags.get("adapter_sha256") != report["adapter_sha256"]
    ):
        raise SystemExit("Acceptance report does not identify this registered adapter")
    client.set_model_version_tag(args.name, args.version, "validation_status", "accepted")
    client.set_model_version_tag(
        args.name, args.version, "generation_accuracy", str(decision["accuracy"])
    )
    client.set_registered_model_alias(args.name, "champion", args.version)
    client.set_tag(args.run_id, "validation_status", "accepted")
    client.log_metric(args.run_id, "generation_accuracy", decision["accuracy"])
    print(
        json.dumps(
            {
                "model_name": args.name,
                "version": args.version,
                "validation_status": "accepted",
                **decision,
            }
        )
    )


if __name__ == "__main__":
    main()
