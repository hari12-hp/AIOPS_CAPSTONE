import json
from pathlib import Path


def test_generation_benchmark_has_unique_ids_and_patterns():
    cases = json.loads(Path("configs/generation_benchmark.json").read_text())
    assert len(cases) >= 5
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(case["question"] and case["accepted_patterns"] for case in cases)
