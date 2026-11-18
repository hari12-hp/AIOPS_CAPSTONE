"""Acceptance evidence must be internally consistent, including negative cases."""

from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.training.verify_submission import validate_report


@pytest.fixture
def report():
    return {
        "cases": [
            {"id": "one", "answer": "4", "accepted_patterns": ["^4$"], "passed": True},
            {"id": "two", "answer": "5", "accepted_patterns": ["^6$"], "passed": False},
        ],
        "accuracy": 0.5,
        "minimum_accuracy": 0.8,
        "status": "needs_review",
    }


def test_saved_qwen_generation_evidence_is_consistent():
    stored = json.loads(Path("reports/evidence/qwen_v2_generation.json").read_text())
    assert validate_report(stored)["accepted"]


def test_failed_candidate_is_rejected(report):
    assert not validate_report(report)["accepted"]


@pytest.mark.parametrize(
    "mutation", ["accuracy", "decision", "case", "empty", "duplicate", "threshold", "nan"]
)
def test_tampered_evidence_is_rejected(report, mutation):
    changed = deepcopy(report)
    if mutation == "accuracy":
        changed["accuracy"] = 1.0
    elif mutation == "decision":
        changed["status"] = "accepted"
    elif mutation == "case":
        changed["cases"][1]["passed"] = True
    elif mutation == "empty":
        changed["cases"] = []
    elif mutation == "duplicate":
        changed["cases"][1]["id"] = "one"
    elif mutation == "threshold":
        changed["minimum_accuracy"] = 0
    elif mutation == "nan":
        changed["accuracy"] = float("nan")
    with pytest.raises(ValueError):
        validate_report(changed)
