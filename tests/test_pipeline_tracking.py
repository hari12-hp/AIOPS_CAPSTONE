"""Regression coverage for dict reports and EDA's list-shaped review artifact."""

from src.pipeline.stage import numeric_metrics


def test_sample_review_list_is_an_artifact_without_numeric_metrics():
    assert numeric_metrics([{"problem": "2+2", "warnings": []}]) == {}


def test_scalar_report_metrics_exclude_flags_and_nested_structures():
    assert numeric_metrics({"seconds": 1.2, "count": 10, "ready": True, "rows": []}) == {
        "seconds": 1.2,
        "count": 10,
    }
