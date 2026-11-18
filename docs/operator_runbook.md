# Operator Runbook

For the complete guided setup, use `./scripts/bootstrap_project.sh`. For an existing environment, use `./scripts/ta_evaluate.sh` to rerun the pipeline, launch all services and verify the result. Both support `--dry-run`; the [TA quickstart](ta_quickstart.md) describes their options and resource links. The individual commands below remain available for diagnosis.

## Requirements and local setup

Use Python 3.14.6, Java 17 or newer for Spark, Docker with Compose, about 8 GiB of available memory for CPU training and several GiB of free disk. The measured run uses four CPU threads. A project-local Java 17 runtime is already available on the demonstration machine; it is intentionally excluded from source control and the submission archive.

For a new machine, unpack the submission archive and run `./scripts/setup.sh`. Install Java and set `JAVA_HOME` before running Spark. The pinned dependencies are in `requirements.lock`; `python_env.yaml` and `MLproject` describe MLprojects execution. The current working environment passes `pip check`. The first public model/dataset download needs network access; serving is offline once the Qwen cache is populated.

## Rebuild the complete selected-model pipeline

```bash
.venv/bin/python -m src.pipeline.run --force
```

The full Qwen run includes inspection, 800-row ingestion, EDA, Spark cleaning, deterministic splitting, a three-step CPU benchmark, one-epoch LoRA training, base and adapter held-out evaluation, generated-answer acceptance and MLflow registration. The benchmark enforces a six-GiB process RSS limit. On this machine training takes approximately 25-30 minutes. The full data snapshot contains 799 cleaned rows; normalized question deduplication leaves 798 split rows. Fully truncated training examples are counted separately.

For a short recording of data preparation:

```bash
.venv/bin/python -m src.pipeline.run --target split --force
```

This updates data-stage timing reports. For a cached reproducibility check, omit `--force`. Use `dvc dag` to visualize the actual dependencies. Every run is local. No command pushes source, models or artifacts to GitHub or a cloud platform.

## Start and verify the demonstration

```bash
./scripts/start_demo.sh
.venv/bin/python scripts/verify_runtime.py
```

The start script populates the pinned public model cache if needed and starts the nine Compose services. Local URLs:

| Screen | URL |
|---|---|
| Workspace | http://localhost:8080 |
| Pipeline console | http://localhost:8081/ |
| API specification | http://localhost:8000/docs |
| MLflow experiments and registry | http://localhost:5000 |
| MLflow model serving | http://localhost:5002/ping |
| Prometheus | http://localhost:19090 |
| Grafana dashboard | http://localhost:13000/d/local-math-assistant |

`docker compose ps` displays service health. The model service loads the `champion` registry alias before the backend/frontend readiness dependencies complete. Model exporter metrics are internal to the Compose network. Ports 19090 and 13000 avoid conflicting with another assignment's existing monitoring services.

## Restore artifacts and registry in another folder

```bash
.venv/bin/dvc pull
./scripts/restore_registry.sh
./scripts/start_demo.sh
```

The local DVC remote is `.dvc/cache-store`, supplied inside the submission archive. MLflow's SQLite history on the demonstration machine contains absolute artifact locations, so do not copy that database into an unrelated path and expect it to work. Restore the adapter and reports with DVC, then run the registration script to create a new local executable model. If new experiment IDs differ, update `mlflowExperimentId` in `frontend/config.js` for direct run links; the original demonstration history is available on its original machine. It verifies base identity, case results and adapter hash. On a restored machine the console labels the submitted stage history as saved evidence; original run IDs are displayed without broken links, while fresh local runs replace that history. A source-only Git clone does not contain ignored artifact objects; use the ZIP, or rebuild the pipeline.

## Verification and reports

```bash
./scripts/evaluate_submission.sh
./scripts/evaluate_submission.sh --full
./scripts/run_mlproject.sh test
```

The fast verification runs tests, shows DVC status/DAG, checks saved acceptance evidence and validates Compose/dashboard configuration. `--full` regenerates all five smoke answers into a separate runtime file. It does not overwrite submitted evaluation evidence. Live HTTP checks are separate and require the stack to be running.

## Monitoring and incident response

Open the Grafana [Alert Center](http://localhost:13000/d/math-alert-center), the local [delivery inbox](http://localhost:19199/), or [Alertmanager](http://localhost:19093/) for active alerts and bounded maintenance silences. The detailed [operations runbook](../monitoring/RUNBOOK.md) explains thresholds and recovery. Monitoring history and silences now persist in named Docker volumes; avoid `docker compose down -v` when preserving evidence.

```bash
.venv/bin/python scripts/verify_monitoring.py --drill
```

This verifies probes, rules, dashboards, Watchdog delivery and a temporary real firing/resolved drill. The TA orchestration runs the non-drill monitoring verification automatically. External notifications are not configured.

## Failure investigation

Check `reports/runtime/pipeline.log`, stage JSON files, and the matching failed MLflow run. The pipeline console shows the bounded log tail. A diagnostic run named `diagnostic_failure` deliberately exits with code 3 to verify failure tracking; it is not a failed final training stage. Model-service errors appear in `docker compose logs model-serving backend`.

A missing `champion` alias requires finishing the pipeline or restoring registration. An offline model cache error requires running the start script with a working public-model download connection. A malformed optional report becomes null in the console and is logged. CPU inference is serialized; do not benchmark concurrency by spawning extra model processes on limited RAM.

## Rollback and shutdown

Review the previous model version's acceptance tags and immutable adapter hash in MLflow. Reset `champion` to that validated version using `MlflowClient.set_registered_model_alias`, with the local tracking URI set to this repository's SQLite database. Restart `model-serving`, and run `scripts/verify_runtime.py` again. Changing the alias alone does not reload an already running model process.

Use `docker compose stop` to pause the stack or `docker compose down` to remove its containers/network. The bind-mounted artifacts and MLflow history remain in the project folder. To rerun training on a low-memory machine, stop the model-serving service first and restart it after training completes.
