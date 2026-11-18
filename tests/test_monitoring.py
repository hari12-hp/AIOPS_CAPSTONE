"""Alert receiver durability, validation, drill expiry and operational telemetry."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from prometheus_client import generate_latest

from src.monitoring.alert_receiver import Inbox, MAX_BODY, handler_for


def notification(name="ExampleIncident", status="firing"):
    return {
        "status": status,
        "alerts": [
            {
                "status": status,
                "labels": {"alertname": name, "severity": "warning", "component": "api"},
                "annotations": {"summary": "An example incident"},
            }
        ],
    }


@contextmanager
def server_for(inbox):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(inbox))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def post(base, path, payload, headers=None):
    data = json.dumps(payload).encode()
    return urlopen(
        Request(base + path, data=data, headers=headers or {"Content-Type": "application/json"}),
        timeout=5,
    )


@pytest.fixture
def inbox(tmp_path):
    value = Inbox(tmp_path)
    yield value
    value.close()


def test_firing_and_resolved_notifications_survive_restart(tmp_path):
    original = Inbox(tmp_path)
    original.receive(notification())
    original.receive(notification(status="resolved"))
    original.close()
    restored = Inbox(tmp_path)
    try:
        assert [e["status"] for e in restored.events()] == ["resolved", "firing"]
    finally:
        restored.close()


def test_concurrent_delivery_keeps_valid_bounded_history(inbox):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: inbox.receive(notification()), range(210)))
    assert len(inbox.events()) == 200
    assert len(inbox.path.read_text().splitlines()) == 210
    assert 'kind="incident",status="firing"} 210.0' in generate_latest(inbox.registry).decode()


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"status": "unknown", "alerts": []},
        {"status": "firing", "alerts": [None]},
        {"status": "firing", "alerts": [{"status": "firing", "labels": {}}]},
        {"status": "firing", "alerts": notification()["alerts"] * 101},
    ],
)
def test_invalid_payloads_do_not_create_false_deliveries(inbox, payload):
    with server_for(inbox) as base:
        with pytest.raises(HTTPError) as error:
            post(base, "/alerts", payload)
        assert error.value.code == 400
    assert inbox.events() == []


def test_receiver_retries_storage_failure_instead_of_claiming_delivery(inbox, monkeypatch):
    def unavailable(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(inbox.logger, "warning", unavailable)
    with server_for(inbox) as base:
        with pytest.raises(HTTPError) as error:
            post(base, "/alerts", notification())
        assert error.value.code == 503
    assert inbox.events() == []
    assert 'kind="incident",status="firing"} 0.0' in generate_latest(inbox.registry).decode()


def test_body_limit_rejects_before_reading_and_bad_content_type_is_rejected(inbox):
    with server_for(inbox) as base:
        with pytest.raises(HTTPError) as error:
            post(
                base,
                "/alerts",
                {},
                {"Content-Length": str(MAX_BODY + 1), "Content-Type": "application/json"},
            )
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            post(base, "/alerts", notification(), {"Content-Type": "text/plain"})
        assert error.value.code == 400


def test_watchdog_is_separate_and_temporary_drill_auto_expires(inbox, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("src.monitoring.alert_receiver.time.monotonic", lambda: clock[0])
    inbox.receive(notification("Watchdog"))
    assert inbox.events()[0]["kind"] == "heartbeat"
    with server_for(inbox) as base:
        assert json.load(post(base, "/drill", {"enabled": True}))["enabled"]
        assert "math_alert_delivery_drill 1.0" in generate_latest(inbox.registry).decode()
        clock[0] += 181
        assert "math_alert_delivery_drill 0.0" in generate_latest(inbox.registry).decode()
        # Changing the signal does not inject an alert notification.
        assert len(inbox.events()) == 1
        assert not json.load(post(base, "/drill", {"enabled": False}))["enabled"]


def test_http_status_metrics_separate_validation_and_server_failures(monkeypatch):
    from fastapi.testclient import TestClient
    from src.app.main import HTTP_RESPONSES, INFLIGHT, LATENCY, app, service
    from src.app.model_service import ModelUnavailable

    client = TestClient(app)
    client_counter = HTTP_RESPONSES.labels("/v1/solve", "4xx")._value.get()
    server_counter = HTTP_RESPONSES.labels("/v1/solve", "5xx")._value.get()
    assert client.post("/v1/solve", json={"question": ""}).status_code == 422
    assert HTTP_RESPONSES.labels("/v1/solve", "4xx")._value.get() == client_counter + 1
    assert HTTP_RESPONSES.labels("/v1/solve", "5xx")._value.get() == server_counter

    def unavailable(question):
        raise ModelUnavailable("Unavailable")

    monkeypatch.setattr(service, "solve", unavailable)
    assert client.post("/v1/solve", json={"question": "2+2"}).status_code == 503
    assert HTTP_RESPONSES.labels("/v1/solve", "5xx")._value.get() == server_counter + 1
    assert INFLIGHT.labels("/v1/solve")._value.get() == 0
    assert 180 in LATENCY._upper_bounds


def test_collector_reports_running_and_parent_failure(tmp_path, monkeypatch):
    from src.app.config import Settings
    from src.app import main

    monkeypatch.setattr(main, "settings", Settings(root=tmp_path))
    folder = tmp_path / "reports/runtime/stages"
    folder.mkdir(parents=True)
    (folder / "train.json").write_text(
        json.dumps({"name": "train", "status": "running", "started_at": 100})
    )
    (folder.parent / "pipeline.json").write_text('{"status":"failed"}')
    metrics = {m.name: m for m in main.PipelineCollector().collect()}
    assert metrics["math_pipeline_run_success"].samples[0].value == 0
    assert metrics["math_pipeline_stage_running_seconds"].samples[0].value > 0
