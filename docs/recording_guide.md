# Demonstration Recording Guide

Start the stack with `./scripts/start_demo.sh`. Keep the project terminal and the following local pages ready. The video itself is a personal submission deliverable; record your screen and explain the choices in your own words.

| Segment | Show | Explain |
|---|---|---|
| 0:00-0:40 | Workspace at localhost:8080 | The user problem, local CPU inference, question examples and navigation |
| 0:40-1:30 | Submit an empty question, then solve `2x + 3 = 11` | Clear input feedback, generated result, response time, copy function |
| 1:30-2:20 | Fraction example; resize the window | Intuitive workflow and responsive layout |
| 2:20-3:40 | Pipeline screen | Cleaned/split counts, actual timings, successful stages and execution log |
| 3:40-4:40 | `dvc dag`, `dvc status`, `dvc.yaml`, `dvc.lock` | Dependencies, versioned data/model artifacts and reproducible commands |
| 4:40-5:50 | MLflow mathematics-pipeline experiment | Parent/child runs, training loss curve, parameters, source snapshot and output artifacts |
| 5:50-6:40 | MLflow registry | Verified candidate version, acceptance tag, hash and `champion` alias; show a historical failed diagnostic run separately |
| 6:40-7:40 | Grafana dashboard and Prometheus targets | Live request rate/latency, pipeline durations, Spark throughput, model metric and all scrape targets up |
| 7:40-8:30 | FastAPI `/docs`, Compose services | Loose coupling: Nginx → FastAPI → MLflow model serving; distinct containers |
| 8:30-9:20 | Test report and mandatory design/manual documents | Test coverage, acceptance scope, model limitations and design rationale |

For an additional progress clip, run `.venv/bin/python -m src.pipeline.run --target split --force` and show the console/MLflow update. This is the real data pipeline and takes seconds, including Spark startup. For training footage, use a full `--force` run with the inference service stopped; capture the live training curve and terminal progress, then restart the stack afterward. Do not describe a cached DVC run as new training.

The five-case generation suite is a bounded smoke test. Explain its scope clearly when showing 100%: it means five accepted outputs, not perfect mathematics performance. Distinguish held-out completion loss from correctness.

## Alerting demonstration

Show the service-operations overview, Alert Center and ML lifecycle dashboard. Open the local inbox at http://localhost:19199/ to show Watchdog delivery. Run `.venv/bin/python scripts/verify_monitoring.py --drill` and record the clearly labelled firing and resolved drill notifications. It typically takes one to two minutes. Explain grouping, hold periods, traffic gates and timed silences; the drill is a synthetic delivery test, not a real outage. No application service is stopped.
