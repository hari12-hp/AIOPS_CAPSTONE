# Evaluation and Training Evidence

## Protocol

All five candidates below were scored sequentially on the same deterministic held-out split of 73 rows. The score is mean response-completion cross-entropy after the shared system-and-user prompt; lower is better. Evaluation used CPU `float32`, maximum sequence length 256, and no sampling. This protocol supports a like-for-like language-model comparison, but it is **not** a claim of mathematical-answer correctness.

## Results

| Candidate | Base revision | Adapter | Held-out completion loss | Eval time |
|---|---|---|---:|---:|
| Gemma 3 1B base | `dcc83ea841ab6100d6b47a070329e1ba4cf78752` | none | 2.7882 | 152.0 s |
| Gemma Pilot V1 | same | supplied Pilot V1 | 1.9765 | 150.8 s |
| Gemma CPU V2 | same | rank 8 CPU LoRA | **1.6628** | 144.9 s |
| Qwen 2.5 0.5B base | recorded in DVC report | none | 1.4872 | 66.1 s |
| Qwen CPU V2 | same | rank 8 CPU LoRA | **1.3497** | 68.2 s |

Gemma CPU V2 improves over the supplied Pilot V1 by 0.3137 loss points (15.9%) and over Gemma base by 1.1254 points (40.4%) on this held-out protocol. The source JSON evidence is DVC-tracked in `reports/evaluation/`.

## Resource evidence

The rerun three-step Gemma benchmark measured 4.655 seconds per microstep and 5.89 GiB RSS (`reports/runtime/gemma_benchmark.json`). The reproducible benchmark command enforces an 8 GiB process-RSS threshold before full training. The completed V2 run accepted 635 examples, rejected 7 fully completion-truncated rows, used batch size 1 with gradient accumulation 4, and completed 159 optimizer steps.

## Traceability and decision

The Gemma V2 registration is `local-math-assistant-gemma-cpu-v2`, version 1, MLflow run `0280baa2c7244260bf5be5c6da54f529`. The Qwen challenger is `local-math-assistant-qwen-cpu-v2`, version 1, MLflow run `0efa44a00cc94484a5df37edbc044361`. Both are deliberately tagged `needs_review`: no generated-answer benchmark with independently checkable mathematical targets has been completed. This conservative status prevents a loss-only result from being presented as production-quality math performance.
