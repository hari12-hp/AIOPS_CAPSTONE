# Test Plan, Cases and Acceptance Criteria

## Acceptance criteria

1. Unit tests pass without downloading a model or full dataset.
2. Spark cleaning produces a quality report and deterministic split hashes.
3. LoRA preflight has nonzero trainable parameters and response-only labels.
4. API health and pipeline endpoints respond without loading model weights.
5. A trained adapter is reloadable with its declared base model and evaluated on the held-out split.
6. Prometheus is available at exactly `/metrics` (no redirect) so the configured scraper has a stable endpoint.
7. The Docker UI reverse proxy sends REST calls to the separately deployed backend; the frontend never embeds model configuration.

## Test cases

| ID | Purpose | Expected result |
|---|---|---|
| DATA-01 | Normalize question text | whitespace/case normalisation is deterministic |
| DATA-02 | Stable record identity | equivalent source inputs hash identically |
| PROMPT-01 | Completion-only masking | prompt labels are ignored and completion labels are trainable |
| LORA-01 | Pilot adapter configuration | rank/alpha/target projections match expected values |
| EVAL-01 | Git metadata fallback | metadata contract remains explicit without Git |
| API-01 | Health endpoint | returns status and does not initialize a model |
| API-02 | Pipeline endpoint | exposes reports when present |
| API-03 | Pipeline observability contract | returns quality, splits, training, evaluation and configuration keys |
| API-04 | Metrics endpoint | returns Prometheus text at `/metrics` |
| EVAL-02 | Generated-answer suite definition | has unique case identifiers and predeclared acceptance patterns |
| OPS-01 | Grafana provisioning | dashboard JSON and provider configuration are present and reference the provisioned Prometheus datasource |
| OPS-02 | Docker boundary | frontend Nginx config proxies only health, API and metrics paths to `backend:8000` |

Run `pytest -q`; save the terminal output in the submission report. Run `docker compose config` to validate the four-service deployment topology before Docker execution. Functional acceptance is met only when all tests pass and the relevant DVC/MLflow runs are recorded.
