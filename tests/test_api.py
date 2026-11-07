from fastapi.testclient import TestClient
from src.app.main import app

client=TestClient(app)
def test_health_is_available_without_model_loading():
    response=client.get("/health")
    assert response.status_code==200 and response.json()["status"]=="ok"
def test_pipeline_status_endpoint():
    response=client.get("/v1/pipeline/status")
    assert response.status_code==200
    assert {"quality","splits","evaluation","training","model_configured"} <= response.json().keys()
def test_empty_question_is_rejected():
    assert client.post("/v1/solve",json={"question":""}).status_code==422
def test_prometheus_metrics_use_canonical_path():
    response=client.get("/metrics")
    assert response.status_code==200
    assert "math_assistant_requests_total" in response.text
