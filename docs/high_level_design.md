# High-Level Design

## Problem and intended outcome

Students practising mathematics need a simple way to request a worked explanation without sending questions to a hosted inference API. Math Studio serves a locally fine-tuned small language model through a web workspace. Operators can inspect the complete data and model lifecycle in a separate pipeline console. The scope is a CPU demonstration of an AIOps application, with honest boundaries around model quality.

Success means the user can submit a question, receive a generated answer, recover from invalid input, and inspect measured operational evidence. Engineering acceptance requires passing automated tests, a completed reproducible DVC graph, an acceptance decision bound to the actual adapter weights, a registered executable MLflow model, and working monitoring exporters. Model smoke acceptance requires at least 80% on the five predeclared cases. This small suite is not a broad mathematics benchmark.

## Functional blocks and boundaries

The independent Nginx frontend contains HTML, CSS and JavaScript. It calls only configurable REST URLs. It never reads model files, imports Python, or connects directly to a database. Nginx provides a same-origin reverse proxy; `frontend/config.js` permits a separate API origin. FastAPI owns validation, response contracts, error translation and request instrumentation. `ModelService` isolates the inference transport from the API route functions.

The deployed inference engine is MLflow Models Serve on port 5002, loading the accepted registry alias `champion`. Its pyfunc wrapper loads the pinned Qwen base and the registered LoRA artifact. This makes the model an independently exposed inference service, rather than merely storing files in an experiment tracker. A lock serializes CPU inference. An optional lazy direct Transformers mode supports local development.

The operator runs the DVC DAG through `src.pipeline.run`. The runner takes a filesystem lock, creates a parent MLflow run, preserves source and dependency identities, and executes the declared stages. Each stage has a child experiment run, durable status, duration, output hashes and explicit exception reporting. A separate console reads these files through REST and links to the tool interfaces. The UI does not launch unrestricted shell commands.

## Design choices and rationale

| Choice | Rationale | Tradeoff |
|---|---|---|
| Qwen 2.5 0.5B with rank-8 LoRA | Fits local CPU resources; only 1,081,344 parameters are trained | Limited reasoning capability; answers require checking |
| Pinned model/data revisions | Establish immutable source identities | Initial setup needs public artifact downloads |
| Bounded 800-row ingestion | Makes a complete CPU experiment practical | The sample does not represent the entire NuminaMath corpus |
| Local Spark | Demonstrates distributed-style data transformations with bounded resources | Startup overhead is significant for a small dataset |
| Hash-based split by normalized question | Keeps question duplicates in one partition and supports reproducibility | Exact partition sizes vary from nominal 80/10/10 |
| Completion-only labels | Avoids optimizing the model to reproduce the prompt | Long prompts can mask every completion token; these are counted and excluded |
| DVC + MLflow | Separates artifact dependency/version control from experiment history/registry | Portable submissions must include the DVC object store and recreate absolute-path registry entries |
| Independent inference service | Separates REST orchestration from model loading | Adds one local service and a network boundary |
| SQLite and local files | Keeps the assignment self-contained | Single-machine demonstration, not a multi-host production database |
| Polling console every five seconds | Near real-time visibility with little operational complexity | State can be up to five seconds behind the pipeline |

## Deployment and resource model

Compose packages frontend, backend, model serving, MLflow tracking, Prometheus, Grafana, Alertmanager, Blackbox Exporter and a persistent alert inbox as nine services. Host ports bind to loopback. Monitoring uses 19090 and 13000 to coexist with the machine's other assignments. The model cache is mounted read-only into inference; only the selected base/adapter is loaded. Avoid running a second training process while the inference service is resident on a low-memory machine.

The source code is organized primarily around functions for data and training stages, with small objects at configuration and model-service boundaries. This supports replaceable inference transports and narrow tests. Request logs omit the question text. Detailed unexpected exceptions remain in operator logs while the user receives a stable error message.

## Model decision and rollback

Evaluation preserves raw completions and a SHA-256 hash of the adapter. The verifier recomputes case decisions and accuracy. Registration refuses mismatched base revisions or adapter weights, records a model version, and changes `champion` only for an accepted candidate. Failed candidates remain visible for review. For rollback, select a previously validated registry version and reset the alias with the MLflow client, then restart `model-serving`; see the operator runbook. No new version is silently described as accepted.

## Limits and future work

This is a single-user CPU demonstration. It has no account system, multi-tenant authorization, TLS termination, distributed serving, or large-scale mathematical correctness evaluation. The training examples can contain synthetic and imperfect solutions; EDA records those fields. The validation partition is reserved and not used for repeated hyperparameter tuning in this run. A broader unseen generation benchmark and measured input drift baseline would be the next quality improvements.
