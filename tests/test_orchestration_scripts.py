"""Exercise operator control flow without downloads, training or Docker mutations."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / ".venv/bin").mkdir(parents=True)
    (tmp_path / "bin").mkdir()
    for name in ("ta_evaluate.sh", "bootstrap_project.sh"):
        shutil.copy2(ROOT / "scripts" / name, tmp_path / "scripts" / name)
    # Each external command records its arguments. Only the result JSON writer
    # executes Python; all expensive operations and preflight probes are mocked.
    stub = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as log:
    log.write(json.dumps([Path(sys.argv[0]).name, *args]) + '\\n')
if args[:1] == ['-']:
    source = sys.stdin.read()
    if "'completed_steps': completed" in source:
        sys.argv = args
        exec(compile(source, '<result-writer>', 'exec'))
if os.environ.get('FAIL_PIPELINE') and args[:2] == ['-m', 'src.pipeline.run']:
    sys.exit(23)
if os.environ.get('FAIL_PIP') and args[:3] == ['-m', 'pip', 'install']:
    sys.exit(24)
if os.environ.get('FAIL_RUNTIME') and args[:1] == ['scripts/verify_runtime.py']:
    sys.exit(25)
"""
    for path in [
        tmp_path / ".venv/bin/python",
        tmp_path / "bin/python3",
        tmp_path / "bin/docker",
        tmp_path / "bin/git",
        tmp_path / "bin/java",
    ]:
        path.write_text(stub)
        path.chmod(0o755)
    for name in ("evaluate_submission.sh", "run_mlproject.sh", "restore_registry.sh"):
        path = tmp_path / "scripts" / name
        path.write_text("#!/usr/bin/env bash\nexec .venv/bin/python " + name + ' "$@"\n')
        path.chmod(0o755)
    return tmp_path


def invoke(checkout, script, *args, **overrides):
    env = dict(
        os.environ,
        PATH=f"{checkout}/bin:{os.environ['PATH']}",
        CALLS=str(checkout / "calls.jsonl"),
        PYTHON_BIN=str(checkout / "bin/python3"),
        HF_HOME=str(checkout / "hf-cache"),
    )
    env.pop("MATH_ASSISTANT_HF_CACHE", None)
    env.pop("JAVA_HOME", None)
    env.update(overrides)
    return subprocess.run(
        ["bash", str(checkout / "scripts" / script), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


@pytest.mark.parametrize("cached", [False, True])
def test_ta_success_runs_pipeline_before_serving_and_live_checks(checkout, cached):
    args = ["--skip-build", *(["--cached"] if cached else [])]
    result = invoke(checkout, "ta_evaluate.sh", *args)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = [json.loads(line) for line in (checkout / "calls.jsonl").read_text().splitlines()]
    train = next(i for i, call in enumerate(calls) if call[1:3] == ["-m", "src.pipeline.run"])
    start = next(i for i, call in enumerate(calls) if call[1:3] == ["compose", "up"])
    live = next(i for i, call in enumerate(calls) if call[1:2] == ["scripts/verify_runtime.py"])
    assert calls.index(["docker", "compose", "stop"]) < train < start < live
    assert ("--force" in calls[train]) is not cached
    assert "--force-recreate" in calls[start]
    assert ["python", "evaluate_submission.sh", "--full"] in calls
    assert ["python", "run_mlproject.sh", "test"] in calls
    summary = json.loads(
        next((checkout / "reports/runtime").glob("ta-evaluation-*.json")).read_text()
    )
    assert summary["status"] == "passed"
    assert summary["cached"] is cached


@pytest.mark.parametrize(
    "failure,code,phase",
    [
        ("FAIL_PIPELINE", 23, "Run the complete DVC and MLflow pipeline"),
        ("FAIL_RUNTIME", 25, "Verify live HTTP inference and monitoring"),
    ],
)
def test_ta_failure_preserves_exit_code_and_diagnostic_result(checkout, failure, code, phase):
    result = invoke(checkout, "ta_evaluate.sh", "--skip-build", **{failure: "1"})
    assert result.returncode == code, result.stdout + result.stderr
    summary = json.loads(
        next((checkout / "reports/runtime").glob("ta-evaluation-*.json")).read_text()
    )
    assert summary["status"] == "failed"
    assert summary["phase"] == phase
    assert "PASS. Evaluation result:" not in result.stdout
    if failure == "FAIL_PIPELINE":
        assert '"compose", "up"' not in (checkout / "calls.jsonl").read_text()


def test_bootstrap_dependency_failure_stops_before_download_and_evaluation(checkout):
    result = invoke(checkout, "bootstrap_project.sh", FAIL_PIP="1")
    assert result.returncode == 24
    calls = (checkout / "calls.jsonl").read_text()
    assert '"src.pipeline.run"' not in calls
    assert '"-m", "pip", "check"' not in calls
    assert "Bootstrap failed" in result.stdout + result.stderr


def test_bootstrap_dry_run_lists_exact_resources_and_has_no_side_effects(checkout):
    result = invoke(checkout, "bootstrap_project.sh", "--dry-run")
    assert result.returncode == 0
    model = yaml.safe_load((ROOT / "configs/train_qwen_v2.yaml").read_text())
    data = yaml.safe_load((ROOT / "configs/data.yaml").read_text())
    assert f"https://huggingface.co/{model['model_id']}/tree/{model['revision']}" in result.stdout
    assert (
        f"https://huggingface.co/datasets/{data['dataset_id']}/tree/{data['revision']}"
        in result.stdout
    )
    assert "docker compose build backend frontend" in result.stdout
    assert not (checkout / "calls.jsonl").exists()
    assert not (checkout / "reports").exists()


@pytest.mark.parametrize("script", ["ta_evaluate.sh", "bootstrap_project.sh"])
def test_unknown_options_fail_without_work(checkout, script):
    result = invoke(checkout, script, "--unknown")
    assert result.returncode == 2
    assert not (checkout / "calls.jsonl").exists()
