#!/usr/bin/env bash
# Start the complete local application and operations tools for screen recording.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PROJECT_ROOT="$PWD"
if [[ ! -f reports/pipeline/registration.json ]]; then
  echo 'Restore artifacts and run scripts/restore_registry.sh, or finish the full pipeline first.' >&2
fi
# Downloads only the pinned, public Qwen base if it is not already cached.
.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
kwargs = dict(repo_id='Qwen/Qwen2.5-0.5B-Instruct', revision='7ae557604adf67be50417f59c2c2f167def9a775', allow_patterns=['*.json', '*.safetensors', '*.txt', '*.jinja'])
try:
    snapshot_download(**kwargs, local_files_only=True)
except OSError:
    snapshot_download(**kwargs)
PY
if ! .venv/bin/python - <<'PYREG'
from pathlib import Path
from mlflow.tracking import MlflowClient
try:
    MlflowClient(tracking_uri=f"sqlite:///{Path.cwd() / 'mlflow.db'}").get_model_version_by_alias('local-math-assistant-qwen-cpu-v2', 'champion')
except Exception:
    raise SystemExit(1)
PYREG
then
  ./scripts/restore_registry.sh
fi
docker compose up -d --build --wait --wait-timeout 300
printf '\nWorkspace:  http://localhost:8080\nPipeline:   http://localhost:8081/\nMLflow:     http://localhost:5000\nAPI docs:   http://localhost:8000/docs\nPrometheus: http://localhost:19090\nGrafana:    http://localhost:13000/d/local-math-assistant\nAlerts:     http://localhost:13000/d/math-alert-center\nInbox:      http://localhost:19199/\n'
