"""FastAPI boundary: UI and infrastructure never call model internals directly."""
import json
from pathlib import Path
from time import perf_counter
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from .config import settings
from .model_service import ModelService, ModelUnavailable

REQUESTS=Counter("math_assistant_requests_total","Requests by endpoint and outcome",["endpoint","outcome"])
LATENCY=Histogram("math_assistant_request_seconds","Request duration by endpoint",["endpoint"])
app=FastAPI(title="Local Mathematics Assistant",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["GET","POST"],allow_headers=["*"])
service=ModelService(settings)

class SolveRequest(BaseModel): question: str = Field(min_length=1,max_length=8000)
class SolveResponse(BaseModel): answer: str; latency_seconds: float; model_loaded: bool

@app.get("/health")
def health():
    REQUESTS.labels("health","ok").inc()
    return {"status":"ok","model_loaded":service.ready,"configured":bool(settings.base_model and settings.adapter_path)}

@app.get("/v1/pipeline/status")
def pipeline_status():
    report=settings.root/"reports/eda/quality.json"; splits=settings.root/"reports/eda/splits.json"
    return {"quality":json.loads(report.read_text()) if report.exists() else None,"splits":json.loads(splits.read_text()) if splits.exists() else None,"model_loaded":service.ready}

@app.post("/v1/solve",response_model=SolveResponse)
def solve(payload: SolveRequest):
    started=perf_counter()
    try: answer, latency=service.solve(payload.question)
    except ModelUnavailable as exc:
        REQUESTS.labels("solve","unavailable").inc(); raise HTTPException(status_code=503,detail=str(exc)) from exc
    except Exception as exc:
        REQUESTS.labels("solve","error").inc(); raise HTTPException(status_code=500,detail="Inference failed; inspect server logs.") from exc
    LATENCY.labels("solve").observe(perf_counter()-started); REQUESTS.labels("solve","ok").inc()
    return SolveResponse(answer=answer,latency_seconds=latency,model_loaded=service.ready)

app.mount("/metrics",make_asgi_app())
app.mount("/",StaticFiles(directory=settings.root/"frontend",html=True),name="frontend")
