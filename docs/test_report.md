# Test Report

Execution: 2026-11-18; extended monitoring verification completed after the original 19:43 IST model checks. Tests use the pinned project environment. Raw JUnit results are in `reports/test-results.xml`; live and pipeline evidence is copied into `reports/evidence/`.

| Verification layer | Result | Evidence |
|---|---|---|
| Unit and contract tests | 58 passed, 0 failed, 0 skipped | JUnit XML; test plan inventories the cases |
| Live service/inference/exporter checks | 10 passed, 0 failed | `reports/evidence/runtime-verification.json` |
| Browser checks | 9 passed, 0 failed | `reports/evidence/browser-verification.json`, `docs/screenshots/` |
| Pipeline lifecycle | completed | Parent MLflow run `32e0318271474a03b44ccfd0e98f759c` and stage evidence |
| Three-step CPU benchmark | 2.109 s/microstep; 3.51 GiB RSS | Passed the six-GiB benchmark limit |
| Spark cleaning | 799 / 800 records; 75.4 records/s | Quality report and MLflow clean stage |
| Generated-answer smoke suite | 5 / 5; threshold 80% | Raw outputs and recomputed verifier |
| Docker and monitoring configuration | Built and exercised | Nine Compose services, fifteen healthy scrape targets, eight ready HTTP endpoints, three Grafana dashboards |
| MLprojects test entry point | Passed in the active project virtual environment | `scripts/run_mlproject.sh test` |

## Monitoring extension

The extended checks pass: seventeen alert rules and six recording rules load successfully, nine alert scenarios and two recording scenarios pass with promtool, and a real Watchdog heartbeat reaches the persistent local inbox. A controlled synthetic signal was observed as both firing and resolved through Prometheus and Alertmanager; the application stayed available. The verifier and delivery evidence are in `reports/evidence/monitoring-verification.json`. All dashboard PromQL expressions are evaluated by the live verifier. Input validation (4xx) is measured separately from service failure (5xx); latency buckets extend to 180 seconds for CPU inference.

Live integration found stale backend DNS in Nginx after container recreation. The proxy now resolves the backend through Docker DNS and the HTTP API probe traverses that proxy. The rerun passes the real inference checks. Monitoring state persists in named volumes; no external notification destination is configured.

## Acceptance decision

The measured acceptance criteria in `docs/test_plan.md` are met by the final checked run. The model serving boundary was exercised with real algebra and fraction questions through the Nginx proxy, FastAPI and MLflow Models Serve. Tests verify controlled handling of invalid input, unavailable inference, internal failures and malformed inference responses. The browser was checked at desktop size and a 390-pixel viewport; no horizontal overflow was observed.

A separate diagnostic stage intentionally exited with code 3 and was recorded as failed in MLflow, with an error and duration. It validates negative-path tracking and is excluded from final candidate acceptance. An initial MLprojects invocation used the machine's unrelated default Python and failed before running tests; the supplied wrapper activates the pinned project environment and the rerun passed. The long execution session also stopped after the complete training epoch was saved; its interrupted evaluation run is retained as killed, and evaluation/registration were resumed from the DVC checkpoint without repeating training. Integration also exposed a list-shaped EDA report logging error; the wrapper was corrected and two regression cases were added. Its logging-only change did not alter the saved training computation. The source was formatted with Ruff after numerical execution; the saved formatting-equivalence report verifies unchanged Python syntax trees, and DVC metadata was refreshed without repeating the unchanged computation. These failures are retained in experiment history rather than hidden.

## Quality limits

Completion loss and generation accuracy have distinct meanings. The five-question suite is a smoke test, not evidence of broad mathematical correctness. The viva and personal screen-recording submission remain the presenter's responsibility. No remote GitHub CI execution, cloud deployment or published repository is claimed.
