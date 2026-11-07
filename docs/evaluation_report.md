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

## Independent generated-answer acceptance

To avoid treating loss as correctness, `configs/generation_benchmark.json` fixes five simple algebra, arithmetic, fraction, geometry and percentage prompts before inference. The evaluator uses deterministic greedy CPU generation, saves every raw answer, and applies predeclared answer patterns with an acceptance threshold of 80%.

| Candidate | Resolved base revision | Correct / total | Accuracy | Decision |
|---|---|---:|---:|---|
| Qwen CPU V2 | `7ae557604adf67be50417f59c2c2f167def9a775` | 5 / 5 | **100%** | accepted |
| Gemma CPU V2 | `dcc83ea841ab6100d6b47a070329e1ba4cf78752` | 2 / 5 | 40% | needs review |

The Qwen V2 report also measured 3.54 seconds for all five greedy generations. This is a deliberately small smoke/acceptance suite, not evidence of broad mathematical competence; its value is that the raw completions, rubric, threshold and decision are reproducible and auditable.

## Resource evidence

The rerun three-step Gemma benchmark measured 4.655 seconds per microstep and 5.89 GiB RSS (`reports/runtime/gemma_benchmark.json`). The reproducible benchmark command enforces an 8 GiB process-RSS threshold before full training. The completed V2 run accepted 635 examples, rejected 7 fully completion-truncated rows, used batch size 1 with gradient accumulation 4, and completed 159 optimizer steps.

## Traceability and decision

The Gemma V2 registration is `local-math-assistant-gemma-cpu-v2`, version 1, MLflow run `0280baa2c7244260bf5be5c6da54f529`, and remains `needs_review`. The Qwen V2 registration is `local-math-assistant-qwen-cpu-v2`, version 1, MLflow run `0efa44a00cc94484a5df37edbc044361`; its model-version tag is updated to `accepted` only after the stored Qwen generation report clears the predeclared threshold. This preserves an evidence-based deployment decision while retaining Gemma's negative result.
