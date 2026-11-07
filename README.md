# Local Mathematics Assistant — CPU Training V2

This repository is a CPU-only, local Mathematics Assistant with bounded data ingestion, Spark cleaning, completion-only LoRA preparation, DVC/MLflow lineage, a FastAPI service, static web UI, Prometheus metrics, Grafana provisioning, and Docker Compose packaging.

## Status and safety gates

Pilot V1 adapter files are stored under `artifacts/input/pilot-v1`. Its manifest and historical comparison CSV were not supplied, so its historical metrics cannot be verified. No model weights or dataset are downloaded by tests. Training is gated behind a preflight/benchmark because the machine has limited available RAM. `docs/evaluation_report.md` records the measured held-out results and explicitly distinguishes completion loss from mathematical correctness.

## Reproduce

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
python -m src.data.inspect_dataset
pytest -q
python -m src.data.ingest_dataset --revision 1b05109f9e5c1ad06c0663519502416c30b300f8
python -m src.data.eda data/raw/numinamath.jsonl
python -m src.data.clean_with_spark data/raw/numinamath.jsonl
python -m src.data.split_dataset data/cleaned/records/part-00000-*.json
dvc dag
```

Run `python -m src.training.train_lora_cpu --help` for preflight commands. Do not start full training before a measured 3–5 step benchmark establishes memory and runtime headroom. The current trainer uses `float32`, batch size 1, rank 8, alpha 16 and the attention q/k/v/o projections. The recorded Gemma preflight stayed below the explicit 8 GiB process-RSS gate.

## Lineage

Use a local MLflow store only, e.g. `mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts`. Record git/DVC identity, data hashes, base revision, adapter hashes and benchmark results in every training/evaluation run. Registration remains blocked until a trained adapter has been reloaded and evaluated on a held-out test split.

PySpark requires Java 17 or later. For this run, a project-local JRE 17 was used through `JAVA_HOME`; it is deliberately ignored from version control because it is a machine runtime, not a source artifact. Install Java 17+, set `JAVA_HOME`, then rerun the Spark and split stages on a fresh machine.

## Application and monitoring

Start the full local stack with `docker compose up --build`. The UI is available at `http://localhost:8080`, the API docs at `http://localhost:8000/docs`, Prometheus at `http://localhost:9090`, and Grafana at `http://localhost:3000`. Nginx proxies the UI's REST and metrics calls to the backend; no browser-side model path or token is exposed. Grafana provisions a request-rate, outcome, and latency dashboard at startup. See `docs/user_manual.md`, `docs/architecture.md`, `docs/low_level_design.md`, `docs/test_plan.md`, `docs/test_report.md`, and `docs/evaluation_report.md`.
