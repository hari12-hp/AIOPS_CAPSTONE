"""Update a local MLflow model-version decision from a saved acceptance report."""
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evaluation", required=True)
    args = parser.parse_args()
    report = json.loads(Path(args.evaluation).read_text())
    if report["status"] != "accepted":
        raise SystemExit("Refusing promotion: generation benchmark did not meet its declared threshold.")
    import mlflow
    from mlflow.tracking import MlflowClient
    mlflow.set_tracking_uri(f"sqlite:///{Path.cwd() / 'mlflow.db'}")
    client = MlflowClient()
    client.set_model_version_tag(args.name, args.version, "validation_status", "accepted")
    client.set_model_version_tag(args.name, args.version, "generation_accuracy", str(report["accuracy"]))
    client.set_model_version_tag(args.name, args.version, "acceptance_protocol", report["protocol"])
    client.set_tag(args.run_id, "validation_status", "accepted")
    client.log_metric(args.run_id, "generation_accuracy", report["accuracy"])
    print(json.dumps({"model_name": args.name, "version": args.version, "validation_status": "accepted", "generation_accuracy": report["accuracy"]}))


if __name__ == "__main__":
    main()
