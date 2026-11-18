# Low-Level Design and API Contract

## Services

| Service | Host URL | Responsibility |
|---|---|---|
| Nginx frontend | http://localhost:8080 | Workspace, pipeline console, guide and reverse proxy |
| FastAPI | http://localhost:8000 | Input validation, REST orchestration, reports, request metrics |
| MLflow Models Serve | http://localhost:5002 | Registered pyfunc inference |
| MLflow tracking | http://localhost:5000 | Experiment history and model registry |
| Prometheus | http://localhost:19090 | Exporter scrapes and alert rules |
| Grafana | http://localhost:13000 | Provisioned operations dashboard |

## Public application API

| Endpoint | Input | Success response | Errors |
|---|---|---|---|
| `GET /health` | none | `status`, `model_loaded`, `configured`, `inference_engine` | 200 indicates process liveness; model readiness is separate |
| `POST /v1/solve` | JSON `question`: string, trimmed, 1-8000 characters | `answer`: string; `latency_seconds`: number; `model_loaded`: boolean | 422 invalid or whitespace-only input; 503 inference unavailable; 500 unexpected inference failure |
| `GET /v1/pipeline/status` | none | `quality`, `splits`, `ingestion`, `evaluation`, `training`, `candidates`, `configured_candidate`, `model_loaded`, `model_configured`, `pipeline`, `stages`, `registration`, `evidence_source` | Missing/malformed optional reports are null; missing stage state is pending |
| `GET /v1/pipeline/logs` | none | `lines`: up to 80 strings from the bounded log tail | Missing logs produce an empty list |
| `GET /metrics` | none | Prometheus text exposition at this exact path | No redirect |
| `GET /docs`, `/openapi.json` | none | Interactive and machine-readable API contract | FastAPI defaults |

Example request:

```json
{"question":"Solve 2x + 3 = 11 for x. Give only the final value."}
```

Example schema for a successful response (values are illustrative):

```json
{"answer":"4","latency_seconds":0.9,"model_loaded":true}
```

Unavailable responses use `{"detail":"The model service is starting or unavailable. Try again shortly."}`. Unexpected failures do not reveal server paths or exception text. The browser inserts generated text with `textContent`, then renders equations with local KaTeX assets in untrusted mode; model-provided HTML is never executed. Copy retains the original answer text.

## MLflow inference interface

`POST http://localhost:5002/invocations` consumes the registered signature:

```json
{"dataframe_split":{"columns":["prompt"],"data":[["What is 7 multiplied by 8?"]]}}
```

It returns `{"predictions":["..."]}`. FastAPI converts one question to one row and extracts the first prediction. The transport has a 180-second timeout; the browser has a 190-second timeout. The wrapper applies the same requested-format chat instruction as the acceptance evaluator and direct development inference, tokenizes at most 2,048 input tokens, serializes access under a lock, uses greedy generation, and caps completions at 128 tokens. The base revision and adapter are registry artifacts, not browser-controlled parameters. A length-limit notice makes incomplete responses explicit. Restored deployments label submitted pipeline history and show fresh registry state separately.

## Core modules and data contracts

`Settings` is an immutable configuration object. `ModelService` owns local initialization or MLflow HTTP transport. `main.py` owns validation and HTTP behavior; its middleware measures success, validation failures, unavailable models and unexpected failures using bounded endpoint labels. `PipelineCollector` reads durable reports at scrape time, so metrics include command-line pipeline work.

`src.data.common` provides normalization, record identities, streaming JSONL I/O and file hashes. Spark trims and validates fields, normalizes whitespace, removes duplicates, sorts and emits records. Splitting uses a SHA-256 bucket of seed plus normalized question. Rows are sorted before writing, and the split report records counts and SHA-256 hashes. A normalized question cannot occur in two partitions.

The training adapter uses q/k/v/o attention projections, rank 8, alpha 16, dropout 0.05, float32, microbatch 1, accumulation 4, maximum length 256 and learning rate 0.00005. The seed is 42. Fully truncated completions are excluded and counted. Trainer callbacks send live numeric metrics to the stage MLflow run.

Stage state has `name`, `status`, `started_at`, `run_id`, `parent_run_id`, `command`, `git_commit`, `git_dirty`; completed/failed stages additionally have `seconds` and `finished_at`. Completed stages record output hashes; failed stages record an error. Atomic replacement prevents partially written JSON. The parent runner uses `flock` to reject overlapping orchestrator runs.

## Telemetry

- API: request counts by endpoint/outcome and duration histograms; Python process/runtime metrics.
- Pipeline: last stage duration and success gauge, Spark records/second and generation smoke accuracy.
- Model process: prediction count, generation duration histogram, loaded state and process/runtime metrics on internal port 9101.
- Infrastructure: scrape health plus Grafana and Prometheus self-metrics.

Availability alerts require one minute of sustained failure. Seventeen Prometheus alert rules cover service readiness, traffic-gated server errors and CPU latency, in-flight pressure, RSS, pipeline outcomes/stalls, acceptance and alerting health. Six recording rules normalize service indicators. Alertmanager groups, inhibits and routes firing/resolved notifications to a bounded persistent local inbox. A Watchdog verifies delivery; a controlled auto-expiring drill tests firing and resolution. No external notification destination is configured. See `monitoring/RUNBOOK.md` for exact thresholds and recovery commands.
