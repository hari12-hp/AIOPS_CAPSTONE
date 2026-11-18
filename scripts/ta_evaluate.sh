#!/usr/bin/env bash
# Run the complete local workflow and verify the result for a teaching assistant.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
  cat <<'HELP'
Usage: ./scripts/ta_evaluate.sh [--cached] [--skip-build] [--dry-run]

Default: rerun every pipeline stage, build the Docker images, start all nine
services, and run source, generation, MLprojects, HTTP and monitoring checks.
  --cached      Let DVC reuse unchanged stages instead of retraining.
  --skip-build  Use existing Docker images; fail if an image is missing.
  --dry-run     Print the workflow without changing files or starting services.
  -h, --help    Show this help.

Prerequisites: run scripts/bootstrap_project.sh once, or provide .venv with the
pinned requirements, Java 17+, Git, flock and a running Docker Compose daemon.
Full training takes about 25–30 minutes on the demonstration CPU; downloads and
image builds take additional time. Existing project services stop during training
and remain running after success. No volumes are removed; no Git commits or remote pushes occur.
Logs and a JSON result are saved under reports/runtime/ta-evaluation-*.
HELP
}
cached=false
skip_build=false
dry_run=false
for arg in "$@"; do
  case "$arg" in
    --cached) cached=true ;;
    --skip-build) skip_build=true ;;
    --dry-run) dry_run=true ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done
export PROJECT_ROOT="$PWD"
export MLFLOW_TRACKING_URI="sqlite:///$PROJECT_ROOT/mlflow.db"
export HF_HOME="${MATH_ASSISTANT_HF_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}}"
export MATH_ASSISTANT_HF_CACHE="$HF_HOME"
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
if [[ -z "${JAVA_HOME:-}" && -x "$PWD/.tools/java17/bin/java" ]]; then
  export JAVA_HOME="$PWD/.tools/java17"
fi
if [[ -n "${JAVA_HOME:-}" ]]; then export PATH="$JAVA_HOME/bin:$PATH"; fi
# DVC stage commands invoke "python" as a subprocess: prefer this checkout's venv.
export PATH="$PWD/.venv/bin:$PATH"

phase=preflight
completed=()
write_result() {
  .venv/bin/python - "$result_file" "$1" "$phase" "$cached" "$skip_build" "$log_file" "${completed[@]}" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
path, status, phase, cached, skip_build, log, *completed = sys.argv[1:]
Path(path).write_text(json.dumps({
    'finished_at': datetime.now(timezone.utc).isoformat(),
    'status': status, 'phase': phase, 'cached': cached == 'true',
    'skip_build': skip_build == 'true', 'completed_steps': completed, 'log': log,
}, indent=2) + '\n')
PY
}
failed() {
  local code="$1"
  trap - ERR INT TERM
  printf '\nFAILED during %s (exit %s). Log: %s\n' "$phase" "$code" "$log_file" >&2
  write_result failed || true
  printf 'Services and evidence are preserved for diagnosis; see docs/operator_runbook.md.\n' >&2
  exit "$code"
}
run_step() {
  phase="$1"; shift
  printf '\n== %s ==\n' "$phase"
  if "$dry_run"; then
    printf '  '; printf '%q ' "$@"; printf '\n'
  else
    "$@"
    completed+=("$phase")
  fi
}
ensure_registry() {
  if ! .venv/bin/python - <<'PY'
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException
try:
    MlflowClient().get_model_version_by_alias('local-math-assistant-qwen-cpu-v2', 'champion')
except MlflowException as exc:
    if exc.error_code != 'RESOURCE_DOES_NOT_EXIST':
        raise
    raise SystemExit(1)
PY
  then
    ./scripts/restore_registry.sh
  fi
}
configure_experiment_links() {
  .venv/bin/python - <<'PY'
from pathlib import Path
import re
from mlflow.tracking import MlflowClient
experiment = MlflowClient().get_experiment_by_name('mathematics-pipeline')
if experiment is None:
    raise SystemExit('The mathematics-pipeline experiment is missing.')
path = Path('frontend/config.js')
text, count = re.subn(r'mlflowExperimentId:\s*\d+',
                     f'mlflowExperimentId: {experiment.experiment_id}', path.read_text())
if count != 1:
    raise SystemExit('Expected exactly one mlflowExperimentId in frontend/config.js.')
path.write_text(text)
print(f'Pipeline console links use local MLflow experiment {experiment.experiment_id}.')
PY
}

if ! "$dry_run"; then
  for tool in git docker java flock; do
    command -v "$tool" >/dev/null || { printf 'Missing prerequisite: %s. See --help.\n' "$tool" >&2; exit 1; }
  done
  [[ -x .venv/bin/python ]] || { echo 'Run ./scripts/bootstrap_project.sh first.' >&2; exit 1; }
  if [[ "$HF_HOME" != /* ]]; then
    echo 'HF_HOME / MATH_ASSISTANT_HF_CACHE must be an absolute cache path.' >&2
    exit 1
  fi
  .venv/bin/python - <<'PY'
import re, subprocess, sys
if sys.version_info[:3] != (3, 14, 6):
    raise SystemExit('This project pins Python 3.14.6; recreate .venv with that interpreter.')
version = subprocess.run(['java', '-version'], capture_output=True, text=True, check=True)
match = re.search(r'version "(\d+)', version.stdout + version.stderr)
if not match or int(match[1]) < 17:
    raise SystemExit('Java 17 or newer is required for Spark.')
PY
  docker compose version >/dev/null
  docker info >/dev/null
  docker compose config --quiet
  mkdir -p reports/runtime
  exec 9>reports/runtime/ta-evaluation.lock
  flock -n 9 || { echo 'Another TA evaluation is running in this checkout.' >&2; exit 1; }
  run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  log_file="$PWD/reports/runtime/ta-evaluation-$run_id.log"
  result_file="$PWD/reports/runtime/ta-evaluation-$run_id.json"
  exec > >(tee "$log_file") 2>&1
  trap 'failed "$?"' ERR
  trap 'failed 130' INT
  trap 'failed 143' TERM
  printf 'TA workflow log: %s\n' "$log_file"
fi

run_step 'Validate the pinned Python environment' .venv/bin/python -m pip check
run_step 'Stop project services to free memory for training' docker compose stop
pipeline=(.venv/bin/python -m src.pipeline.run)
if ! "$cached"; then pipeline+=(--force); fi
printf '\nPipeline stages: inspect, ingest, EDA, Spark, split, benchmark, train,\nbase evaluation, adapter evaluation, generation acceptance, registry.\nLive training output: reports/runtime/pipeline.log\n'
run_step 'Run the complete DVC and MLflow pipeline' "${pipeline[@]}"
run_step 'Ensure a local executable champion exists' ensure_registry
run_step 'Match console links to the local MLflow experiment' configure_experiment_links
run_step 'Check source, artifacts and fresh generation answers' ./scripts/evaluate_submission.sh --full
run_step 'Verify the MLprojects test entry point' ./scripts/run_mlproject.sh test
if ! "$skip_build"; then
  run_step 'Build the backend and frontend images' docker compose build backend frontend
fi
# Recreate serving so it loads the newly accepted champion, even on a repeat run.
run_step 'Start all nine services with the current champion' docker compose up -d --no-build --force-recreate --wait --wait-timeout 300
run_step 'Verify live HTTP inference and monitoring' .venv/bin/python scripts/verify_runtime.py
run_step 'Verify the separate pipeline console' .venv/bin/python -c 'from urllib.request import urlopen; r = urlopen("http://localhost:8081/", timeout=10); assert r.status == 200 and b"<h1>Pipeline</h1>" in r.read(); print("Pipeline console: HTTP 200")'
run_step 'Verify dashboards, probes and alert delivery health' .venv/bin/python scripts/verify_monitoring.py
run_step 'Show service health' docker compose ps

if ! "$dry_run"; then
  phase=complete
  write_result passed
  printf '\nPASS. Evaluation result: %s\n' "$result_file"
fi
cat <<'LINKS'

Workspace:    http://localhost:8080/
Pipeline:     http://localhost:8081/
MLflow:       http://localhost:5000/
API docs:     http://localhost:8000/docs
Model health: http://localhost:5002/ping
Prometheus:   http://localhost:19090/
Grafana:      http://localhost:13000/d/local-math-assistant
Alert center: http://localhost:13000/d/math-alert-center
Alertmanager: http://localhost:19093/
Alert inbox:  http://localhost:19199/
LINKS
