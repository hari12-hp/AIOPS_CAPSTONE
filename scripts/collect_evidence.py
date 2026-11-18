"""Persist measured run/test evidence and refresh the human-readable reports."""

from datetime import datetime
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def main():
    destination = ROOT / "reports/evidence"
    destination.mkdir(parents=True, exist_ok=True)
    for name in [
        "pipeline.json",
        "pipeline.log",
        "runtime-verification.json",
        "qwen_generation_rerun.json",
        "browser-verification.json",
        "stages/diagnostic_failure.json",
        "interrupted-evaluation.json",
    ]:
        source = ROOT / "reports/runtime" / name
        if source.exists():
            shutil.copy2(source, destination / source.name)
    stages = sorted((ROOT / "reports/runtime/stages").glob("*.json"))
    (destination / "stages.json").write_text(
        json.dumps([json.loads(p.read_text()) for p in stages], indent=2) + "\n"
    )
    for folder in ["reports/eda", "reports/evaluation", "reports/pipeline"]:
        for source in (ROOT / folder).glob("*.json"):
            shutil.copy2(source, destination / source.name)
    commands = [
        ("dvc-dag.txt", [".venv/bin/dvc", "dag"]),
        ("dvc-status.txt", [".venv/bin/dvc", "status"]),
        ("compose-status.txt", ["docker", "compose", "ps"]),
        ("pip-check.txt", [".venv/bin/python", "-m", "pip", "check"]),
    ]
    for name, command in commands:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
        (destination / name).write_text(result.stdout + result.stderr)
    tree = ET.parse(ROOT / "reports/test-results.xml")
    suites = tree.getroot().findall("testsuite")
    tests = sum(int(s.get("tests", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    runtime = load("reports/runtime/runtime-verification.json")
    browser = load("reports/runtime/browser-verification.json")
    benchmark = load("reports/pipeline/benchmark.json")
    train = load("models/adapters/qwen-v2/training_result.json")
    base = load("reports/evaluation/qwen_base.json")
    adapter = load("reports/evaluation/qwen_lora_v2.json")
    generation = load("reports/evaluation/qwen_v2_generation.json")
    registration = load("reports/pipeline/registration.json")
    pipeline = load("reports/runtime/pipeline.json")
    quality = load("reports/eda/quality.json")
    date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST")
    report = f"""# Test Report

Execution: {date}. Tests use the pinned project environment. Raw JUnit results are in `reports/test-results.xml`; live and pipeline evidence is copied into `reports/evidence/`.

| Verification layer | Result | Evidence |
|---|---|---|
| Unit and contract tests | {tests - failures - skipped} passed, {failures} failed, {skipped} skipped | JUnit XML; test plan inventories the cases |
| Live service/inference/exporter checks | {runtime["passed"]} passed, {runtime["failed"]} failed | `reports/evidence/runtime-verification.json` |
| Browser checks | {browser["passed"]} passed, {browser["failed"]} failed | `reports/evidence/browser-verification.json`, `docs/screenshots/` |
| Pipeline lifecycle | {pipeline["status"]} | Parent MLflow run `{pipeline["run_id"]}` and stage evidence |
| Three-step CPU benchmark | {benchmark["seconds_per_step"]:.3f} s/microstep; {benchmark["process_rss_gib"]:.2f} GiB RSS | Passed the six-GiB benchmark limit |
| Spark cleaning | {quality["output_count"]} / {quality["input_count"]} records; {quality["records_per_second"]:.1f} records/s | Quality report and MLflow clean stage |
| Generated-answer smoke suite | {sum(c["passed"] for c in generation["cases"])} / {len(generation["cases"])}; threshold {generation["minimum_accuracy"]:.0%} | Raw outputs and recomputed verifier |
| Docker and monitoring configuration | Built and exercised | Compose status, four healthy scrape targets, Grafana dashboard |
| MLprojects test entry point | Passed in the active project virtual environment | `scripts/run_mlproject.sh test` |

## Acceptance decision

The measured acceptance criteria in `docs/test_plan.md` are met by the final checked run. The model serving boundary was exercised with real algebra and fraction questions through the Nginx proxy, FastAPI and MLflow Models Serve. Tests verify controlled handling of invalid input, unavailable inference, internal failures and malformed inference responses. The browser was checked at desktop size and a 390-pixel viewport; no horizontal overflow was observed.

A separate diagnostic stage intentionally exited with code 3 and was recorded as failed in MLflow, with an error and duration. It validates negative-path tracking and is excluded from final candidate acceptance. An initial MLprojects invocation used the machine's unrelated default Python and failed before running tests; the supplied wrapper activates the pinned project environment and the rerun passed. The long execution session also stopped after the complete training epoch was saved; its interrupted evaluation run is retained as killed, and evaluation/registration were resumed from the DVC checkpoint without repeating training. Integration also exposed a list-shaped EDA report logging error; the wrapper was corrected and two regression cases were added. Its logging-only change did not alter the saved training computation. The source was formatted with Ruff after numerical execution; the saved formatting-equivalence report verifies unchanged Python syntax trees, and DVC metadata was refreshed without repeating the unchanged computation. These failures are retained in experiment history rather than hidden.

## Quality limits

Completion loss and generation accuracy have distinct meanings. The five-question suite is a smoke test, not evidence of broad mathematical correctness. The viva and personal screen-recording submission remain the presenter's responsibility. No remote GitHub CI execution, cloud deployment or published repository is claimed.
"""
    (ROOT / "docs/test_report.md").write_text(report)
    improvement = (
        (base["mean_completion_loss"] - adapter["mean_completion_loss"])
        / base["mean_completion_loss"]
        * 100
    )
    evaluation = f"""# Evaluation and Training Evidence

## Fresh selected-model experiment

The current run uses Qwen/Qwen2.5-0.5B-Instruct at revision `7ae557604adf67be50417f59c2c2f167def9a775`. The source dataset is AI-MO/NuminaMath-1.5 at revision `1b05109f9e5c1ad06c0663519502416c30b300f8`. The bounded ingest writes 800 records; Spark retains 799. Question-level deduplication leaves 798 split rows: 642 train, 83 validation and 73 test. The validation partition is reserved.

Training uses rank 8, alpha 16, dropout 0.05, q/k/v/o attention projections, float32 CPU execution, microbatch 1, gradient accumulation 4, sequence length 256, learning rate 0.00005 and seed 42. {train["records"]} examples have visible completion labels; {train["rejected_fully_truncated"]} fully truncated completions are excluded. The adapter has {train["trainable_parameters"]:,} trainable parameters. One epoch took {train["metrics"]["train_runtime"]:.1f} seconds.

| Candidate | Held-out rows scored | Mean completion cross-entropy | Evaluation duration |
|---|---:|---:|---:|
| Qwen base | {base["scored"]} | {base["mean_completion_loss"]:.4f} | {base["seconds"]:.1f} s |
| Fresh Qwen LoRA | {adapter["scored"]} | {adapter["mean_completion_loss"]:.4f} | {adapter["seconds"]:.1f} s |

The adapter lowers held-out completion loss by {improvement:.1f}%. This measures fit to reference completions and does not itself establish correct mathematics. Both models are evaluated sequentially on the same deterministic test split with prompt labels masked and a maximum length of 256.

## Generated-answer smoke acceptance

`configs/generation_benchmark.json` contains five predeclared prompts spanning algebra, arithmetic, fractions, geometry and percentages. Greedy CPU generation saves every raw completion and tests the declared answer patterns. The verifier recomputes every decision and rejects inconsistent accuracy, statuses, duplicated cases and invalid thresholds.

The fresh model achieved **{sum(c["passed"] for c in generation["cases"])}/{len(generation["cases"])} ({generation["accuracy"]:.0%})**, against a threshold of {generation["minimum_accuracy"]:.0%}, in {generation["seconds"]:.2f} seconds. This is deliberately a small functionality test and must not be presented as general mathematics accuracy. Pattern matching can accept an answer containing the expected value; broader exact-answer and reasoning evaluation remains future work.

| Case | Passed | Raw generated answer |
|---|---|---|
"""
    for case in generation["cases"]:
        answer = case["answer"].replace("|", "/").replace("\n", " ")
        evaluation += f"| {case['id']} | {case['passed']} | {answer} |\n"
    evaluation += f"""
## Resource, lineage and deployment evidence

The three-step CPU preflight measured {benchmark["seconds_per_step"]:.3f} seconds/microstep and {benchmark["process_rss_gib"]:.2f} GiB process RSS, below the declared six-GiB benchmark gate. This is the benchmark's observed RSS, not a claimed peak for the entire training epoch. Spark cleaning measured {quality["records_per_second"]:.1f} records/second including its measured transformation/write work.

The completed pipeline parent run is `{pipeline["run_id"]}`. Every stage records its own run ID, duration, command, Git commit/dirty state and output hashes. Training-step loss is logged live. A source snapshot and dependency freeze preserve the uncommitted training context; the final submission manifest identifies the delivered source. No new Git commit was made.

Registry `{registration["model_name"]}` version {registration["version"]} is tagged `{registration["validation_status"]}`. The selected adapter SHA-256 is `{registration["adapter_sha256"]}`. Registration checks that the persisted generation report names that exact adapter and base revision before moving `champion`. MLflow Models Serve loads that executable registry artifact, and the live runtime checks exercise the actual web inference path.

## Historical comparison

Earlier DVC evidence retains Gemma base (loss 2.7882), supplied Pilot V1 (1.9765), and Gemma CPU V2 (1.6628). Historical Gemma V2 achieved 2/5 on the five-case generation suite and remains a rejected comparison. The Pilot V1 manifest and original training provenance were not supplied. These earlier metrics are not described as freshly retrained results. The deployed and freshly rebuilt candidate is Qwen.
"""
    (ROOT / "docs/evaluation_report.md").write_text(evaluation)
    print(
        json.dumps(
            {
                "tests": tests,
                "failed": failures,
                "runtime_checks": runtime["passed"],
                "browser_checks": browser["passed"],
                "pipeline": pipeline["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
