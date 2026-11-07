# Assignment Submission Checklist (Viva Excluded)

## Demonstration

- [x] Web UI: `frontend/` with responsive status, pipeline view and solve workflow.
- [x] ML pipeline view: `/v1/pipeline/status` displays Spark quality metrics and split hashes.
- [x] Pipeline operations: DVC DAG, MLflow runs, API health and Prometheus metrics provide run/error/status views.
- [x] User manual: `docs/user_manual.md`.

## Software Engineering

- [x] Architecture/HLD: `docs/architecture.md`.
- [x] LLD/API I/O contract: `docs/low_level_design.md`.
- [x] Loose coupling: static frontend communicates only with FastAPI REST endpoints.
- [x] Code style and error boundaries: typed request models, narrow model-service boundary and HTTP error translation.
- [x] Unit tests, plan and report: `tests/`, `docs/test_plan.md`, `docs/test_report.md`.

## AIOps

- [x] Data engineering: bounded Parquet ingest, Spark cleaning and deterministic split; reports record 88.9 records/s cleaning throughput.
- [x] Source/version control: Git commits, DVC local remote, DVC DAG and DVC adapter/report pointers.
- [x] Experiment tracking: local MLflow SQLite runs/registers adapters and captures parameters, metrics, artifacts and validation status.
- [x] Instrumentation: Prometheus `/metrics`, scrape configuration and Grafana datasource provisioning.
- [x] Packaging: MLproject, FastAPI backend Dockerfile, independent static frontend Dockerfile and Docker Compose stack.

## Evidence and limitations

- [x] Gemma base, Pilot V1 and Gemma CPU V2 use the same held-out 73-row split; detailed reports are DVC tracked in `reports/evaluation/`.
- [x] Gemma V2 is locally registered as `local-math-assistant-gemma-cpu-v2` version 1, status `needs_review`.
- [x] Qwen V2 is also registered as a smaller CPU challenger.
- [ ] A quality-approved staging alias is intentionally not assigned: loss improvements alone do not establish mathematical correctness; independent generated-answer acceptance tests are still required.
- [ ] Docker runtime was not started during the CPU training run to preserve the 12 GB working-memory budget. The API is smoke-tested in-process.
