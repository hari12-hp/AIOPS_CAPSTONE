# Architecture and High-Level Design

```mermaid
flowchart LR
 U[Non-technical user] --> UI[Static web UI]
 UI -->|REST JSON| API[FastAPI service]
 API --> S[Lazy single-model service]
 S --> A[LoRA adapter + pinned base model]
 API --> M[/metrics]
 M --> P[Prometheus] --> G[Grafana]
 D[NuminaMath] --> SP[Spark ingestion/cleaning/split] --> DV[DVC local remote]
 DV --> T[CPU LoRA training] --> ML[MLflow SQLite + registry]
```

The frontend is an independent static service. It interacts with the backend only through configurable REST calls. The backend imports no model at startup, preventing the UI, health endpoint and pipeline console from exhausting CPU RAM. A request loads exactly one base model and one adapter under a lock, ensuring deterministic CPU use.

Data processing uses bounded Parquet range reads and local Spark transformations. DVC tracks raw snapshots, adapters and reports; MLflow tracks experiments and the registry stores loadable adapter wrappers without copying full base weights.
