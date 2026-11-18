# Evaluation and Training Evidence

## Fresh selected-model experiment

The current run uses Qwen/Qwen2.5-0.5B-Instruct at revision `7ae557604adf67be50417f59c2c2f167def9a775`. The source dataset is AI-MO/NuminaMath-1.5 at revision `1b05109f9e5c1ad06c0663519502416c30b300f8`. The bounded ingest writes 800 records; Spark retains 799. Question-level deduplication leaves 798 split rows: 642 train, 83 validation and 73 test. The validation partition is reserved.

Training uses rank 8, alpha 16, dropout 0.05, q/k/v/o attention projections, float32 CPU execution, microbatch 1, gradient accumulation 4, sequence length 256, learning rate 0.00005 and seed 42. 634 examples have visible completion labels; 8 fully truncated completions are excluded. The adapter has 1,081,344 trainable parameters. One epoch took 1642.0 seconds.

| Candidate | Held-out rows scored | Mean completion cross-entropy | Evaluation duration |
|---|---:|---:|---:|
| Qwen base | 73 | 1.4872 | 86.2 s |
| Fresh Qwen LoRA | 73 | 1.3505 | 92.2 s |

The adapter lowers held-out completion loss by 9.2%. This measures fit to reference completions and does not itself establish correct mathematics. Both models are evaluated sequentially on the same deterministic test split with prompt labels masked and a maximum length of 256.

## Generated-answer smoke acceptance

`configs/generation_benchmark.json` contains five predeclared prompts spanning algebra, arithmetic, fractions, geometry and percentages. Greedy CPU generation saves every raw completion and tests the declared answer patterns. The verifier recomputes every decision and rejects inconsistent accuracy, statuses, duplicated cases and invalid thresholds.

The fresh model achieved **5/5 (100%)**, against a threshold of 80%, in 3.70 seconds. This is deliberately a small functionality test and must not be presented as general mathematics accuracy. Pattern matching can accept an answer containing the expected value; broader exact-answer and reasoning evaluation remains future work.

| Case | Passed | Raw generated answer |
|---|---|---|
| ALG-01 | True | $x = 4$ |
| ARITH-01 | True | 56 |
| FRAC-01 | True | $\frac{7}{8}$ |
| GEOM-01 | True | $36$ |
| PCT-01 | True | 30 |

## Resource, lineage and deployment evidence

The three-step CPU preflight measured 2.109 seconds/microstep and 3.51 GiB process RSS, below the declared six-GiB benchmark gate. This is the benchmark's observed RSS, not a claimed peak for the entire training epoch. Spark cleaning measured 75.4 records/second including its measured transformation/write work.

The completed pipeline parent run is `32e0318271474a03b44ccfd0e98f759c`. Every stage records its own run ID, duration, command, Git commit/dirty state and output hashes. Training-step loss is logged live. A source snapshot and dependency freeze preserve the uncommitted training context; the final submission manifest identifies the delivered source. No new Git commit was made.

Registry `local-math-assistant-qwen-cpu-v2` version 3 is tagged `accepted`. The selected adapter SHA-256 is `250f394852745ef16ea716c7d0937a5b3ec7864028e79eb5d25d9bd4999d9267`. Registration checks that the persisted generation report names that exact adapter and base revision before moving `champion`. MLflow Models Serve loads that executable registry artifact, and the live runtime checks exercise the actual web inference path.

## Historical comparison

Earlier DVC evidence retains Gemma base (loss 2.7882), supplied Pilot V1 (1.9765), and Gemma CPU V2 (1.6628). Historical Gemma V2 achieved 2/5 on the five-case generation suite and remains a rejected comparison. The Pilot V1 manifest and original training provenance were not supplied. These earlier metrics are not described as freshly retrained results. The deployed and freshly rebuilt candidate is Qwen.
