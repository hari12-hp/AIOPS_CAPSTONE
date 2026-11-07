# Low-Level Design and API Contract

| Endpoint | Input | Output | Error behavior |
|---|---|---|---|
| `GET /health` | none | service and model configuration state | always 200 if process is live |
| `GET /v1/pipeline/status` | none | data-quality report, deterministic split hashes, training result, held-out evaluation and model configuration state | 200; absent reports are `null` |
| `POST /v1/solve` | `{"question": string (1-8000 chars)}` | `{"answer": string, "latency_seconds": number, "model_loaded": bool}` | 503 when model configuration is absent; 500 for inference failure |
| `GET /metrics` | none | Prometheus exposition format | standard Prometheus ASGI endpoint |

`ModelService` is the only layer permitted to import and load Transformers/PEFT weights. `main.py` validates request boundaries, records endpoint/outcome/latency metrics, emits structured request logs without question text, and translates exceptions to stable HTTP contracts. Static assets never access files, MLflow, DVC, or model internals. In Docker, Nginx proxies `/health`, `/v1/*`, and `/metrics` to the backend service; the frontend has no direct model dependency. Compose mounts the selected DVC-pulled adapter read-only at `/models/adapters` and persists the Hugging Face model cache in `.hf-cache` outside the image.
