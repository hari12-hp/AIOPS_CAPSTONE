from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)


def test_health_is_available_without_model_loading():
    response = client.get("/health")
    assert response.status_code == 200 and response.json()["status"] == "ok"


def test_pipeline_status_endpoint():
    response = client.get("/v1/pipeline/status")
    assert response.status_code == 200
    assert {
        "quality",
        "splits",
        "evaluation",
        "training",
        "model_configured",
    } <= response.json().keys()


def test_empty_question_is_rejected():
    assert client.post("/v1/solve", json={"question": ""}).status_code == 422


def test_prometheus_metrics_use_canonical_path():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "math_assistant_requests_total" in response.text


def test_whitespace_only_and_oversized_questions_are_rejected():
    assert client.post("/v1/solve", json={"question": " \n\t "}).status_code == 422
    assert client.post("/v1/solve", json={"question": "x" * 8001}).status_code == 422


def test_success_returns_the_model_output_without_markup_execution(monkeypatch):
    from src.app.main import service

    monkeypatch.setattr(service, "solve", lambda question: ("<script>4</script>", 0.25))
    response = client.post("/v1/solve", json={"question": "  2 + 2  "})
    assert response.status_code == 200
    assert response.json()["answer"] == "<script>4</script>"
    assert response.json()["latency_seconds"] == 0.25


def test_model_unavailable_has_a_stable_503_contract(monkeypatch):
    from src.app.main import service
    from src.app.model_service import ModelUnavailable

    def unavailable(question):
        raise ModelUnavailable("Model is starting")

    monkeypatch.setattr(service, "solve", unavailable)
    response = client.post("/v1/solve", json={"question": "2+2"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Model is starting"


def test_unexpected_error_does_not_expose_internal_details(monkeypatch):
    from src.app.main import service

    def broken(question):
        raise RuntimeError("private/internal/path")

    monkeypatch.setattr(service, "solve", broken)
    response = client.post("/v1/solve", json={"question": "2+2"})
    assert response.status_code == 500
    assert "private/internal/path" not in response.text


def test_unreadable_reports_and_missing_logs_do_not_break_console(tmp_path, monkeypatch):
    import src.app.main as main
    from src.app.config import Settings

    monkeypatch.setattr(main, "settings", Settings(root=tmp_path))
    folder = tmp_path / "reports/eda"
    folder.mkdir(parents=True)
    (folder / "quality.json").write_text("not json")
    response = client.get("/v1/pipeline/status")
    assert response.status_code == 200
    assert response.json()["quality"] is None
    assert len(response.json()["stages"]) == 11
    assert client.get("/v1/pipeline/logs").json() == {"lines": []}


def test_metrics_include_pipeline_instrumentation_and_validation_failures():
    client.post("/v1/solve", json={"question": ""})
    response = client.get("/metrics")
    assert "math_pipeline_stage_success" in response.text
    assert 'math_assistant_requests_total{endpoint="/v1/solve",outcome="error"}' in response.text


def test_unknown_paths_do_not_create_unbounded_metric_labels():
    client.get("/unknown/arbitrary/path/123")
    response = client.get("/metrics")
    assert 'endpoint="/unknown/arbitrary/path/123"' not in response.text
    assert 'endpoint="other"' in response.text


def test_portable_submission_evidence_is_explicit_and_restored_registry_takes_precedence(
    tmp_path, monkeypatch
):
    import json
    import src.app.main as main
    from src.app.config import Settings

    monkeypatch.setattr(main, "settings", Settings(root=tmp_path))
    evidence = tmp_path / "reports/evidence"
    evidence.mkdir(parents=True)
    (evidence / "stages.json").write_text(
        json.dumps([{"name": "train", "status": "completed", "seconds": 12}])
    )
    (evidence / "pipeline.json").write_text(json.dumps({"status": "completed", "run_id": "saved"}))
    (evidence / "pipeline.log").write_text("saved execution log\n")
    runtime = tmp_path / "reports/runtime"
    runtime.mkdir()
    (runtime / "restored_registration.json").write_text(
        json.dumps({"version": "1", "validation_status": "accepted"})
    )
    result = client.get("/v1/pipeline/status").json()
    assert result["evidence_source"] == "submitted"
    assert result["pipeline"]["run_id"] == "saved"
    assert next(s for s in result["stages"] if s["name"] == "train")["status"] == "completed"
    assert result["registration"]["version"] == "1"
    assert client.get("/v1/pipeline/logs").json()["lines"] == ["saved execution log"]
