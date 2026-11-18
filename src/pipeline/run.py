"""Execute the local DVC graph under one parent experiment, with a process lock."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from src.pipeline.stage import atomic_json
from src.training.model_metadata import git_metadata


def main():
    def interrupted(number, _frame):
        # Turn termination into a recorded failure instead of leaving stale
        # "running" state when an execution session or operator stops the run.
        raise InterruptedError(f"Pipeline interrupted by signal {number}")

    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["split", "register"], default="register")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    runtime = root / "reports/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "pipeline.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("A pipeline is already running.")
        import mlflow

        mlflow.set_tracking_uri(f"sqlite:///{root / 'mlflow.db'}")
        mlflow.set_experiment("mathematics-pipeline")
        with mlflow.start_run(run_name=f"local-{args.target}", tags=git_metadata()) as run:
            state = {
                "status": "running",
                "target": args.target,
                "started_at": time.time(),
                "run_id": run.info.run_id,
                **git_metadata(),
            }
            atomic_json(runtime / "pipeline.json", state)
            # A dirty worktree cannot be identified by its commit alone. Preserve source.
            import tarfile

            snapshot = runtime / "source-snapshot.tar.gz"
            with tarfile.open(snapshot, "w:gz") as archive:
                for folder in (
                    "src",
                    "configs",
                    "scripts",
                    "tests",
                    "frontend",
                    "monitoring",
                    "docs",
                ):
                    for path in sorted((root / folder).rglob("*")):
                        if path.is_file() and "__pycache__" not in path.parts:
                            archive.add(path, arcname=str(path.relative_to(root)))
                for filename in (
                    "dvc.yaml",
                    "params.yaml",
                    "requirements.lock",
                    "MLproject",
                    "docker-compose.yml",
                    "Dockerfile.backend",
                    "Dockerfile.frontend",
                ):
                    archive.add(root / filename, arcname=filename)
            mlflow.log_artifact(str(snapshot), "reproducibility")
            mlflow.log_text(
                subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True),
                "reproducibility/pip-freeze.txt",
            )
            command = [sys.executable, "-m", "dvc", "repro"]
            if args.force:
                command.append("--force")
            command += ["inspect", "eda"]
            if args.target == "register":
                command.append("evaluate_base")
            command.append(args.target)
            env = dict(
                os.environ,
                PIPELINE_PARENT_RUN_ID=run.info.run_id,
                MLFLOW_TRACKING_URI=mlflow.get_tracking_uri(),
                TOKENIZERS_PARALLELISM="false",
                OMP_NUM_THREADS="4",
                MKL_NUM_THREADS="4",
            )
            java = root / ".tools/java17"
            if java.exists() and not env.get("JAVA_HOME"):
                env["JAVA_HOME"] = str(java)
                env["PATH"] = str(java / "bin") + os.pathsep + env["PATH"]
            try:
                with (runtime / "pipeline.log").open("w") as output:
                    result = subprocess.run(
                        command, env=env, stdout=output, stderr=subprocess.STDOUT
                    )
                state.update(
                    status="completed" if result.returncode == 0 else "failed",
                    exit_code=result.returncode,
                )
                if result.returncode:
                    raise RuntimeError("Pipeline failed; inspect reports/runtime/pipeline.log")
            except BaseException as exc:
                state.update(status="failed", error=str(exc))
                raise
            finally:
                state["seconds"] = time.time() - state["started_at"]
                atomic_json(runtime / "pipeline.json", state)
                mlflow.log_metric("pipeline_seconds", state["seconds"])
                mlflow.log_artifact(str(runtime / "pipeline.json"))
                mlflow.log_artifact(str(runtime / "pipeline.log"))
                if (root / "dvc.lock").exists():
                    mlflow.log_artifact(str(root / "dvc.lock"), "reproducibility")
                print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
