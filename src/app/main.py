"""Validated REST contracts, request instrumentation and read-only pipeline console."""

import json
import logging
from pathlib import Path
from time import perf_counter
import time

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import GaugeMetricFamily, REGISTRY

from .config import settings
from .model_service import ModelService, ModelUnavailable

REQUESTS = Counter(
    "math_assistant_requests_total", "Requests by endpoint and outcome", ["endpoint", "outcome"]
)
LATENCY = Histogram(
    "math_assistant_request_seconds",
    "Request duration by endpoint",
    ["endpoint"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60, 120, 180),
)
HTTP_RESPONSES = Counter(
    "math_assistant_http_responses_total",
    "HTTP responses by bounded status class",
    ["endpoint", "status_class"],
)
INFLIGHT = Gauge("math_assistant_inflight_requests", "Requests currently in flight", ["endpoint"])
for status_class in ("2xx", "3xx", "4xx", "5xx"):
    HTTP_RESPONSES.labels("/v1/solve", status_class)
LATENCY.labels("/v1/solve")
INFLIGHT.labels("/v1/solve")
LOGGER = logging.getLogger("math_assistant.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title="Local Mathematics Assistant", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)
service = ModelService(settings)


class SolveRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)

    @field_validator("question")
    @classmethod
    def question_is_not_blank(cls, value):
        if not value.strip():
            raise ValueError("Enter a mathematics question first.")
        return value.strip()


class SolveResponse(BaseModel):
    answer: str
    latency_seconds: float
    model_loaded: bool


def load_json(path: Path):
    """Missing reports remain explicit; malformed reports do not break the console."""
    try:
        return json.loads(path.read_text()) if path.exists() else None
    except OSError, json.JSONDecodeError:
        LOGGER.warning("unreadable_report path=%s", path)
        return None


def stage_reports():
    folder = settings.root / "reports/runtime/stages"
    saved = load_json(settings.root / "reports/evidence/stages.json")
    submitted = (
        {row["name"]: row for row in saved if isinstance(row, dict) and "name" in row}
        if isinstance(saved, list)
        else {}
    )
    names = [
        "inspect",
        "ingest",
        "eda",
        "clean",
        "split",
        "benchmark",
        "train",
        "evaluate_base",
        "evaluate_adapter",
        "acceptance",
        "register",
    ]
    return [
        load_json(folder / f"{name}.json")
        or submitted.get(name)
        or {"name": name, "status": "pending"}
        for name in names
    ]


class PipelineCollector:
    """Read durable stage results on scrape, including work outside the web process."""

    def collect(self):
        duration = GaugeMetricFamily(
            "math_pipeline_stage_seconds", "Last measured duration", labels=["stage"]
        )
        status = GaugeMetricFamily(
            "math_pipeline_stage_success",
            "1 complete, 0 failed, -1 pending/running",
            labels=["stage"],
        )
        running = GaugeMetricFamily(
            "math_pipeline_stage_running_seconds",
            "Elapsed time for currently running stages",
            labels=["stage"],
        )
        for stage in stage_reports():
            status.add_metric(
                [stage["name"]], {"completed": 1, "failed": 0}.get(stage["status"], -1)
            )
            if "seconds" in stage:
                duration.add_metric([stage["name"]], stage["seconds"])
            if stage["status"] == "running" and isinstance(stage.get("started_at"), (int, float)):
                running.add_metric([stage["name"]], max(0, time.time() - stage["started_at"]))
        yield duration
        yield status
        yield running
        pipeline = load_json(settings.root / "reports/runtime/pipeline.json") or load_json(
            settings.root / "reports/evidence/pipeline.json"
        )
        if pipeline:
            yield GaugeMetricFamily(
                "math_pipeline_run_success",
                "1 complete, 0 failed, -1 pending/running",
                value={"completed": 1, "failed": 0}.get(pipeline.get("status"), -1),
            )
        for metric, file, key, description in [
            (
                "math_data_records_per_second",
                "reports/eda/quality.json",
                "records_per_second",
                "Spark cleaning throughput",
            ),
            (
                "math_generation_accuracy",
                "reports/evaluation/qwen_v2_generation.json",
                "accuracy",
                "Five-case generation smoke accuracy",
            ),
        ]:
            report = load_json(settings.root / file)
            if report and isinstance(report.get(key), (int, float)):
                yield GaugeMetricFamily(metric, description, value=report[key])


REGISTRY.register(PipelineCollector())


@app.middleware("http")
async def audit_request(request: Request, call_next):
    started = perf_counter()
    endpoint = (
        request.url.path
        if request.url.path
        in {"/health", "/v1/solve", "/v1/pipeline/status", "/v1/pipeline/logs", "/metrics"}
        else "other"
    )
    outcome = "error"
    status_class = "5xx"
    INFLIGHT.labels(endpoint).inc()
    try:
        response = await call_next(request)
        status_class = f"{response.status_code // 100}xx"
        outcome = (
            "ok"
            if response.status_code < 400
            else "unavailable"
            if response.status_code == 503
            else "error"
        )
        return response
    finally:
        elapsed = perf_counter() - started
        REQUESTS.labels(endpoint, outcome).inc()
        HTTP_RESPONSES.labels(endpoint, status_class).inc()
        INFLIGHT.labels(endpoint).dec()
        LATENCY.labels(endpoint).observe(elapsed)
        LOGGER.info("request path=%s outcome=%s seconds=%.4f", endpoint, outcome, elapsed)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": service.ready,
        "configured": bool(settings.serving_url or (settings.base_model and settings.adapter_path)),
        "inference_engine": "mlflow" if settings.serving_url else "local",
    }


@app.get("/v1/pipeline/status")
def pipeline_status():
    candidates = {}
    for key, folder, evaluation, generation in [
        ("qwen_cpu_v2", "qwen-v2", "qwen_lora_v2.json", "qwen_v2_generation.json"),
        ("gemma_cpu_v2", "gemma-v2", "gemma_v2.json", "gemma_v2_generation.json"),
    ]:
        candidates[key] = {
            "training": load_json(
                settings.root / "models/adapters" / folder / "training_result.json"
            ),
            "completion_evaluation": load_json(settings.root / "reports/evaluation" / evaluation),
            "generation_acceptance": load_json(settings.root / "reports/evaluation" / generation),
        }
    configured = (
        "gemma_cpu_v2" if "gemma" in (settings.adapter_path or "").lower() else "qwen_cpu_v2"
    )
    selected = candidates[configured]
    return {
        "quality": load_json(settings.root / "reports/eda/quality.json"),
        "splits": load_json(settings.root / "reports/eda/splits.json"),
        "ingestion": load_json(settings.root / "reports/eda/ingestion.json"),
        "evaluation": selected["completion_evaluation"],
        "training": selected["training"],
        "candidates": candidates,
        "configured_candidate": configured,
        "model_loaded": service.ready,
        "model_configured": bool(
            settings.serving_url or (settings.base_model and settings.adapter_path)
        ),
        "pipeline": load_json(settings.root / "reports/runtime/pipeline.json")
        or load_json(settings.root / "reports/evidence/pipeline.json"),
        "evidence_source": "runtime"
        if (settings.root / "reports/runtime/pipeline.json").exists()
        else "submitted",
        "stages": stage_reports(),
        "registration": load_json(settings.root / "reports/runtime/restored_registration.json")
        or load_json(settings.root / "reports/pipeline/registration.json"),
    }


@app.get("/v1/pipeline/logs")
def pipeline_logs():
    path = settings.root / "reports/runtime/pipeline.log"
    if not path.exists():
        path = settings.root / "reports/evidence/pipeline.log"
    try:
        # Read a bounded tail so growing training logs do not dominate a request.
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - 24000))
            content = stream.read().decode("utf-8", errors="replace")
        return {"lines": content.replace("\r", "\n").splitlines()[-80:]}
    except OSError:
        return {"lines": []}


@app.post("/v1/solve", response_model=SolveResponse)
def solve(payload: SolveRequest):
    try:
        answer, latency = service.solve(payload.question)
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("inference_failed error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=500, detail="Inference failed; inspect server logs."
        ) from exc
    return SolveResponse(answer=answer, latency_seconds=latency, model_loaded=service.ready)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.mount("/", StaticFiles(directory=settings.root / "frontend", html=True), name="frontend")
