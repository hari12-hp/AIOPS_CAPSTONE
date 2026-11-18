"""Exercise the MLflow REST boundary without loading model weights."""

import io
import json
from urllib.error import URLError
import pytest
from src.app.config import Settings
from src.app.model_service import ModelService, ModelUnavailable


def test_mlflow_inference_contract(monkeypatch):
    import src.app.model_service as module

    seen = []

    def respond(request, timeout):
        seen.append(json.loads(request.data))
        return io.BytesIO(b'{"predictions":["x = 4"]}')

    monkeypatch.setattr(module, "urlopen", respond)
    service = ModelService(Settings(serving_url="http://model-serving:5002"))
    answer, seconds = service.solve("2x+3=11")
    assert answer == "x = 4" and seconds >= 0 and service.ready
    assert seen == [{"dataframe_split": {"columns": ["prompt"], "data": [["2x+3=11"]]}}]


@pytest.mark.parametrize(
    "payload", [b"{}", b'{"predictions":[]}', b"not json", b'{"predictions":[""]}']
)
def test_malformed_mlflow_responses_become_unavailable(monkeypatch, payload):
    import src.app.model_service as module

    monkeypatch.setattr(module, "urlopen", lambda *a, **kw: io.BytesIO(payload))
    service = ModelService(Settings(serving_url="http://model-serving:5002"))
    with pytest.raises(ModelUnavailable):
        service.solve("2+2")
    assert not service.ready


def test_mlflow_network_failure_becomes_unavailable(monkeypatch):
    import src.app.model_service as module

    def unavailable(*args, **kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr(module, "urlopen", unavailable)
    with pytest.raises(ModelUnavailable):
        ModelService(Settings(serving_url="http://model-serving:5002")).solve("2+2")
