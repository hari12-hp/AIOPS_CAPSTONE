# Test Plan, Cases and Acceptance Criteria

## Acceptance criteria

1. Unit/contract tests pass without loading model weights or downloading datasets.
2. Invalid/blank/oversized questions are rejected; successful, unavailable and unexpected-failure response contracts remain stable.
3. Inference crosses the declared MLflow dataframe/prediction interface and malformed/network responses become controlled errors.
4. Spark cleaning records quality and throughput; normalized question sets in train/validation/test are disjoint; counts and hashes are reproducible.
5. Training uses nonzero LoRA parameters and completion-only labels; fully truncated examples are counted.
6. Evaluation compares base and adapter on the same held-out partition. A generation gate is recomputed from raw outputs, and registration verifies the actual base revision and adapter hash.
7. Health, console and metrics remain accessible without loading a model in the API process. Missing/corrupt optional reports do not crash the console.
8. DVC describes the local integration pipeline, tracks artifacts and has no unexpected stale stages after final verification.
9. Compose builds and runs all nine services; Nginx → FastAPI → MLflow produces a real answer; Grafana is provisioned and all fifteen Prometheus scrape targets are healthy.
10. Browser checks cover input feedback, examples, successful inference, safe text output, guide/navigation and mobile layout without horizontal overflow.

## Automated case inventory

| Group | Cases | Coverage |
|---|---:|---|
| Data helpers | 2 | Whitespace/case normalization, deterministic bucket and record identity |
| Prompt labels | 1 | Completion-only masking |
| LoRA configuration | 1 | Selected adapter rank/alpha/target projections |
| Evaluation metadata | 1 | Explicit Git identity contract |
| API | 12 | Health; console; empty/whitespace/oversized input; metrics path; successful solve; 503/500 errors; missing/corrupt reports/logs; validation metrics; bounded metric labels |
| Generation definition | 1 | Unique cases with predeclared patterns |
| Evidence verification | 9 | Saved report consistency; rejected candidate; tampered accuracy/status/case/empty/duplicate/threshold/NaN |
| MLflow transport | 6 | Successful request/response schema; four malformed outputs; network failure |
| Pipeline report tracking | 2 | List-shaped EDA artifacts; numeric metrics without flags/nested values |
| Generation serving contract | 2 | Requested output format and explicit length-limit behavior |
| TA orchestration | 8 | Default/cached order, fail-fast pipeline/runtime behavior, setup failure, resource links, dry-run and invalid options |
| Alerting and telemetry | 13 | Durable concurrent inbox writes, bounded history/body, six malformed payloads, storage failure retry, drill expiry, HTTP status classes and parent/stage metrics |
| Total | 58 | Parameterized cases count as separate executions |

## Execution layers

Run `./scripts/evaluate_submission.sh` for tests and source/evidence configuration checks. JUnit output is saved to `reports/test-results.xml`. Add `--full` for a separate regenerated smoke report. `./scripts/run_mlproject.sh test` exercises the MLproject entry point in the active pinned local environment.

Run the full selected-model pipeline separately to measure Spark, CPU training and held-out evaluation. Its stage files, MLflow runs and DVC outputs are functional evidence, not mocked unit results. A deliberately failed diagnostic stage verifies negative run-state persistence; it is not part of final candidate acceptance.

With Compose running, `scripts/verify_runtime.py` checks service health, two actual generated answers through Nginx/FastAPI/MLflow, tracking and serving, provisioned Grafana, the original exporters, live model metrics and all eleven completed stages. Browser verification is documented with screenshots. `docs/test_report.md` records the actual execution results and any limitations.

Monitoring rule tests use promtool to verify nine alert scenarios and two recording-rule scenarios, including hold/recovery, low-volume error gating, CPU latency, pipeline/model gates, controlled drill lifecycle and 4xx exclusion. Live `scripts/verify_monitoring.py --drill` checks all dashboard expressions, fifteen scrape targets, eight HTTP probes, routing, heartbeat and real firing/resolved delivery.
