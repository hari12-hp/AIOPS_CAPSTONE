# Test Report

**Execution date:** 2026-11-07  
**Command:** `python -m pytest -q`  
**Result:** 10 passed, 0 failed.

| Group | Cases | Result |
|---|---:|---|
| Data normalization and deterministic identity | 2 | Pass |
| Prompt completion masking | 1 | Pass |
| Pilot LoRA configuration | 1 | Pass |
| Metadata/evaluation contract | 1 | Pass |
| API health, pipeline, validation and Prometheus endpoint | 4 | Pass |
| Generated-answer benchmark definition | 1 | Pass |

## Functional evidence

| Candidate | Held-out rows scored | Mean completion loss | Runtime |
|---|---:|---:|---:|
| Gemma 3 1B base | 73 | 2.7882 | 152.0 s |
| Pilot V1 LoRA | 73 | 1.9765 | 150.8 s |
| Gemma CPU V2 LoRA | 73 | 1.6628 | 144.9 s |
| Qwen 0.5B base | 73 | 1.4872 | 66.1 s |
| Qwen CPU V2 LoRA | 73 | 1.3497 | 68.2 s |

Completion loss is a language-model loss, not a mathematical correctness claim. The production-quality acceptance gate remains `needs_review` until independent generated-answer checks and an explicit quality threshold are added.

The generated-answer gate has now been executed separately: Qwen V2 achieved 5/5 at the declared 80% threshold and is accepted for this bounded smoke suite; Gemma V2 achieved 2/5 and remains `needs_review`. See `docs/evaluation_report.md` for raw, DVC-tracked evidence and the exact scope of that decision.

## Operational verification

| Check | Command | Result |
|---|---|---|
| DVC graph and cache state | `dvc dag`, `dvc status` | Pass; graph is current. The expensive completed training/evaluation stages are frozen and their artifacts are independently DVC-tracked. |
| CPU safety gate | Gemma three-step benchmark with `--max-rss-gib 8` | Pass; 4.655 s/microstep, 5.89 GiB RSS. |
| Compose topology | `docker compose config` | Pass; backend, Nginx frontend, Prometheus and Grafana resolve. |
| Grafana assets | JSON/provider parse check | Pass; dashboard is provisioned from source with rate, p95 latency, errors and successful-solve panels. |

The full Docker image build/run was not combined with the completed 12 GB CPU training session; this avoids competing model and container workloads. Its reproducible deployment command is documented in the user manual.
