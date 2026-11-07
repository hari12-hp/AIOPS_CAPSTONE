# Test Plan, Cases and Acceptance Criteria

## Acceptance criteria

1. Unit tests pass without downloading a model or full dataset.
2. Spark cleaning produces a quality report and deterministic split hashes.
3. LoRA preflight has nonzero trainable parameters and response-only labels.
4. API health and pipeline endpoints respond without loading model weights.
5. A trained adapter is reloadable with its declared base model and evaluated on the held-out split.

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

Run `pytest -q`; save the terminal output in the submission report. Functional acceptance is met only when all tests pass and the relevant DVC/MLflow runs are recorded.
