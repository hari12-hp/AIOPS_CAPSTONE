import json
from pathlib import Path


def test_saved_qwen_generation_evidence_meets_declared_threshold():
    report = json.loads(Path("reports/evaluation/qwen_v2_generation.json").read_text())
    assert report["status"] == "accepted"
    assert report["accuracy"] >= report["minimum_accuracy"]
