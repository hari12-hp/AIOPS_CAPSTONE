"""Run a DVC stage with live MLflow metrics and a durable local status record."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

from src.training.model_metadata import git_metadata, file_sha256


def numeric_metrics(payload):
    """A JSON report may be a list (for example the EDA sample review)."""
    if not isinstance(payload, dict):
        return {}
    return {
        key: value
        for key, value in payload.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def main():
    import mlflow

    name, *command = sys.argv[1:]
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise SystemExit("Usage: stage NAME -- COMMAND ...")
    if command[0] == "python":
        command[0] = sys.executable
    root = Path.cwd()
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{root / 'mlflow.db'}"))
    mlflow.set_experiment("mathematics-pipeline")
    parent = os.getenv("PIPELINE_PARENT_RUN_ID")
    tags = {**git_metadata(), "stage": name}
    if parent:
        tags["mlflow.parentRunId"] = parent
    destination = root / "reports/runtime/stages" / f"{name}.json"
    started = time.time()
    with mlflow.start_run(run_name=name, tags=tags) as run:
        state = {
            "name": name,
            "status": "running",
            "started_at": started,
            "run_id": run.info.run_id,
            "parent_run_id": parent,
            "command": command,
            **git_metadata(),
        }
        atomic_json(destination, state)
        mlflow.log_param("command", " ".join(command))
        env = dict(
            os.environ, MLFLOW_RUN_ID=run.info.run_id, MLFLOW_TRACKING_URI=mlflow.get_tracking_uri()
        )
        try:
            result = subprocess.run(command, env=env, check=False)
            if result.returncode:
                raise RuntimeError(f"Stage {name} exited with code {result.returncode}")
            state["status"] = "completed"
            # Save the exact outputs and identities with the run, beyond autologging.
            import yaml

            outputs = yaml.safe_load((root / "dvc.yaml").read_text())["stages"][name].get(
                "outs", []
            )
            state["outputs"] = {}
            for output in outputs:
                path = root / output
                if path.is_file():
                    state["outputs"][output] = file_sha256(path)
                    if path.suffix == ".json":
                        mlflow.log_artifact(str(path), "reports")
                        payload = json.loads(path.read_text())
                        for key, value in numeric_metrics(payload).items():
                            mlflow.log_metric(key, value)
                elif path.is_dir():
                    state["outputs"][output] = {
                        str(f.relative_to(path)): file_sha256(f)
                        for f in path.rglob("*")
                        if f.is_file()
                    }
        except BaseException as exc:
            state.update(status="failed", error=str(exc))
            raise
        finally:
            state["seconds"] = time.time() - started
            state["finished_at"] = time.time()
            atomic_json(destination, state)
            mlflow.log_metric("stage_seconds", state["seconds"])
            mlflow.log_artifact(str(destination), "stage")


if __name__ == "__main__":
    main()
