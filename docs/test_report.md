# Test Report

**Execution date:** 2026-11-07  
**Command:** `python -m pytest -q`  
**Result:** 8 passed, 0 failed.

| Group | Cases | Result |
|---|---:|---|
| Data normalization and deterministic identity | 2 | Pass |
| Prompt completion masking | 1 | Pass |
| Pilot LoRA configuration | 1 | Pass |
| Metadata/evaluation contract | 1 | Pass |
| API health, pipeline and request validation | 3 | Pass |

## Functional evidence

| Candidate | Held-out rows scored | Mean completion loss | Runtime |
|---|---:|---:|---:|
| Gemma 3 1B base | 73 | 2.7882 | 152.0 s |
| Pilot V1 LoRA | 73 | 1.9765 | 150.8 s |
| Gemma CPU V2 LoRA | 73 | 1.6628 | 144.9 s |
| Qwen 0.5B base | 73 | 1.4872 | 66.1 s |
| Qwen CPU V2 LoRA | 73 | 1.3497 | 68.2 s |

Completion loss is a language-model loss, not a mathematical correctness claim. The production-quality acceptance gate remains `needs_review` until independent generated-answer checks and an explicit quality threshold are added.
