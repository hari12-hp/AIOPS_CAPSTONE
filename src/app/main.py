"""FastAPI boundary: UI and infrastructure never call model internals directly."""
import json
import logging
from pathlib import Path
from time import perf_counter
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from .config import settings
from .model_service import ModelService, ModelUnavailable

REQUESTS=Counter("math_assistant_requests_total","Requests by endpoint and outcome",["endpoint","outcome"])
LATENCY=Histogram("math_assistant_request_seconds","Request duration by endpoint",["endpoint"])
LOGGER=logging.getLogger("math_assistant.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app=FastAPI(title="Local Mathematics Assistant",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["GET","POST"],allow_headers=["*"])
service=ModelService(settings)

class SolveRequest(BaseModel): question: str = Field(min_length=1,max_length=8000)
class SolveResponse(BaseModel): answer: str; latency_seconds: float; model_loaded: bool

def load_json(path: Path):
    """Return an optional report without making observability endpoints fragile."""
    try:
        return json.loads(path.read_text()) if path.exists() else None
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("unreadable_report path=%s", path)
        return None

@app.middleware("http")
async def audit_request(request: Request, call_next):
    """Emit request latency for every public API route without logging question text."""
    started=perf_counter()
    response=await call_next(request)
    endpoint=request.url.path
    if endpoint in {"/health", "/v1/pipeline/status"}:
        outcome="ok" if response.status_code < 400 else "error"
        REQUESTS.labels(endpoint, outcome).inc()
        LATENCY.labels(endpoint).observe(perf_counter()-started)
    LOGGER.info("request path=%s status=%s seconds=%.4f", endpoint, response.status_code, perf_counter()-started)
    return response

@app.get("/health")
def health():
    return {"status":"ok","model_loaded":service.ready,"configured":bool(settings.base_model and settings.adapter_path)}

@app.get("/v1/pipeline/status")
def pipeline_status():
    report=settings.root/"reports/eda/quality.json"; splits=settings.root/"reports/eda/splits.json"
    candidates = {
        "qwen_cpu_v2": {"training": load_json(settings.root/"models/adapters/qwen-v2/training_result.json"), "completion_evaluation": load_json(settings.root/"reports/evaluation/qwen_lora_v2.json"), "generation_acceptance": load_json(settings.root/"reports/evaluation/qwen_v2_generation.json")},
        "gemma_cpu_v2": {"training": load_json(settings.root/"models/adapters/gemma-v2/training_result.json"), "completion_evaluation": load_json(settings.root/"reports/evaluation/gemma_v2.json"), "generation_acceptance": load_json(settings.root/"reports/evaluation/gemma_v2_generation.json")},
    }
    configured = "qwen_cpu_v2" if "qwen" in (settings.adapter_path or "").lower() else "gemma_cpu_v2"
    selected = candidates[configured]
    return {"quality":load_json(report),"splits":load_json(splits),"evaluation":selected["completion_evaluation"],"training":selected["training"],"candidates":candidates,"configured_candidate":configured,"model_loaded":service.ready,"model_configured":bool(settings.base_model and settings.adapter_path)}

@app.post("/v1/solve",response_model=SolveResponse)
def solve(payload: SolveRequest):
    started=perf_counter()
    try: answer, latency=service.solve(payload.question)
    except ModelUnavailable as exc:
        REQUESTS.labels("solve","unavailable").inc(); raise HTTPException(status_code=503,detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("inference_failed error_type=%s", type(exc).__name__)
        REQUESTS.labels("solve","error").inc(); raise HTTPException(status_code=500,detail="Inference failed; inspect server logs.") from exc
    LATENCY.labels("solve").observe(perf_counter()-started); REQUESTS.labels("solve","ok").inc()
    return SolveResponse(answer=answer,latency_seconds=latency,model_loaded=service.ready)

@app.get("/metrics", include_in_schema=False)
def metrics():
    """Expose Prometheus text format at the conventional, non-redirecting path."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.mount("/",StaticFiles(directory=settings.root/"frontend",html=True),name="frontend")
