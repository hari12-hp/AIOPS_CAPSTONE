# Viva Preparation

## Explain the project in one minute

Math Studio is a local mathematics practice assistant with an independently deployed web UI and REST backend. A fine-tuned Qwen LoRA adapter is exposed through MLflow Models Serve. DVC orchestrates ingestion, Spark cleaning, deterministic splitting, resource benchmarking, training, evaluation and registration. MLflow records experiments and a verified champion decision. Prometheus and Grafana show API, model, data-pipeline and process behavior. The pipeline screen combines lifecycle evidence and tool links.

## Questions to practise

| Question | Points to explain |
|---|---|
| Why use a small model and LoRA? | CPU/RAM constraints, limited trainable parameters, adapter portability, capability tradeoffs |
| Why Spark for only 800 rows? | Demonstrates the required data-engineering engine; bounded CPU experiment; overhead and scaling tradeoff |
| What do DVC and Git each track? | Git tracks code/configuration and object pointers; DVC tracks artifact contents and dependency identities |
| What does MLflow add? | Nested experiment runs, live metrics, explicit parameters/artifacts, executable pyfunc models and registry aliases |
| How is MLflow actually used for inference? | FastAPI calls `/invocations` on a distinct MLflow Models Serve process using a registered model signature |
| How do you prevent leakage? | Split normalized questions with a deterministic hash, keep question duplicates in one partition, score held-out test rows |
| Why completion-only labels? | Ignore system/user prompt tokens; optimize the response; count fully truncated completions |
| Does lower loss prove correct mathematics? | No; loss measures fit to reference completions; generated-answer tests have a separate declared threshold |
| Is the 100% score general accuracy? | No; it is limited to the five-case smoke suite and must be presented with that sample size |
| How is promotion controlled? | Recompute case decisions, verify threshold/base revision/adapter SHA-256, retain failed candidates, update champion only on acceptance |
| How is inference protected against repeated requests? | Serialized model lock, UI duplicate-submit guard, bounded input/output and timeouts |
| How are failures observed? | Stage failure JSON and failed MLflow runs; stable HTTP errors; metrics and local alert rules |
| How do you reproduce an uncommitted run? | Git commit plus dirty flag, saved source snapshot, pip freeze, pinned revisions, output hashes and DVC lock |
| How would you roll back? | Verify a prior accepted registry version, reset alias, restart model serving and repeat live checks |
| What needs improvement before production? | Broader unseen evaluation, real drift baselines, authentication/TLS, multi-user resource management and scalable experiment storage |

Review your own Assignments 1-10 for the viva criterion specific to those assignments. Their complete question papers and your answers are not part of this repository, so this guide does not claim to cover them. Be able to open each relevant source file and explain the implementation without relying on memorized wording.
