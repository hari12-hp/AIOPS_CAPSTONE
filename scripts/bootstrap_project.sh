#!/usr/bin/env bash
# Build a fresh checkout from the pinned public Hugging Face resources.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
  cat <<'HELP'
Usage: ./scripts/bootstrap_project.sh [--cached] [--skip-build] [--dry-run]

Print the upstream model/dataset links, create the Python environment, download
the pinned Qwen model, then run ingestion, training, evaluation, registration,
image builds, all nine local services and the TA checks with one command.
  --cached      Reuse unchanged DVC stages when available; a fresh clone still
                builds missing outputs. The default reruns every stage.
  --skip-build  Reuse existing Docker images (not suitable for a fresh machine).
  --dry-run     Print the plan without installing, downloading or changing files.
  -h, --help    Show this help.

Install these machine prerequisites first: Python 3.14.6 with venv, Java 17+,
Git, flock, Docker Engine and Docker Compose v2; start the Docker daemon.
Set PYTHON_BIN to choose the Python 3.14.6 executable. Set JAVA_HOME if needed.
Allow about 8 GiB available RAM and 15 GiB free disk, plus Internet access for
public downloads. Training alone takes about 25–30 minutes on the demo CPU.
No Hugging Face account/token is needed for the selected public resources.
HELP
}
args=("$@")
dry_run=false
for arg in "$@"; do
  case "$arg" in
    --cached|--skip-build) ;;
    --dry-run) dry_run=true ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done
# Keep these exact identities aligned with configs/train_qwen_v2.yaml and data.yaml.
cat <<'RESOURCES'
Hugging Face model (public, used by training and serving):
  https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct
  https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775
Hugging Face dataset (public, bounded 800-example download):
  https://huggingface.co/datasets/AI-MO/NuminaMath-1.5
  https://huggingface.co/datasets/AI-MO/NuminaMath-1.5/tree/1b05109f9e5c1ad06c0663519502416c30b300f8

The dataset is range-read by the DVC ingestion stage; the complete corpus is not
needed. The LoRA adapter is trained locally from this base, not downloaded from
an unpublished student model repository. Historical Gemma runs are not required.
RESOURCES

python_bin="${PYTHON_BIN:-python3}"
export PROJECT_ROOT="$PWD"
export MLFLOW_TRACKING_URI="sqlite:///$PROJECT_ROOT/mlflow.db"
export HF_HOME="${MATH_ASSISTANT_HF_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}}"
export MATH_ASSISTANT_HF_CACHE="$HF_HOME"
if [[ -z "${JAVA_HOME:-}" && -x "$PWD/.tools/java17/bin/java" ]]; then
  export JAVA_HOME="$PWD/.tools/java17"
fi
if [[ -n "${JAVA_HOME:-}" ]]; then export PATH="$JAVA_HOME/bin:$PATH"; fi

if "$dry_run"; then
  printf '\n== Create the pinned Python environment ==\n  '
  printf '%q ' "$python_bin" -m venv .venv; printf '\n'
  printf '  .venv/bin/python -m pip install -r requirements.lock\n'
  printf '\n== Download the pinned base model and tokenizer to %s ==\n' "$HF_HOME"
  printf '  huggingface_hub.snapshot_download (pinned revision above; cached files are reused)\n'
  ./scripts/ta_evaluate.sh "${args[@]}"
  exit 0
fi

for tool in "$python_bin" git docker java flock; do
  command -v "$tool" >/dev/null || { printf 'Missing prerequisite: %s. See --help.\n' "$tool" >&2; exit 1; }
done
"$python_bin" - <<'PY'
import re, subprocess, sys
if sys.version_info[:3] != (3, 14, 6):
    raise SystemExit('Use Python 3.14.6 (set PYTHON_BIN=/path/to/python3.14).')
version = subprocess.run(['java', '-version'], capture_output=True, text=True, check=True)
match = re.search(r'version "(\d+)', version.stdout + version.stderr)
if not match or int(match[1]) < 17:
    raise SystemExit('Java 17 or newer is required for Spark.')
PY
docker compose version >/dev/null
docker info >/dev/null
docker compose config --quiet
if [[ "$HF_HOME" != /* ]]; then
  echo 'HF_HOME / MATH_ASSISTANT_HF_CACHE must be an absolute cache path.' >&2
  exit 1
fi
# The portable ZIP has no .git folder; DVC still needs a local Git repository.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git init --quiet; fi
mkdir -p reports/runtime
exec 8>reports/runtime/bootstrap.lock
flock -n 8 || { echo 'Another bootstrap is running in this checkout.' >&2; exit 1; }
bootstrap_log="$PWD/reports/runtime/bootstrap-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
exec > >(tee "$bootstrap_log") 2>&1
trap 'code=$?; printf "\nBootstrap failed (exit %s). Log: %s\n" "$code" "$bootstrap_log" >&2; exit "$code"' ERR
printf '\nBootstrap log: %s\n' "$bootstrap_log"
printf '\n== Install the pinned project environment ==\n'
if [[ ! -x .venv/bin/python ]]; then "$python_bin" -m venv .venv; fi
.venv/bin/python -c 'import sys; assert sys.version_info[:3] == (3, 14, 6), "Existing .venv must use Python 3.14.6"'
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip check
printf '\n== Download the base model and tokenizer ==\n'
.venv/bin/python - <<'PY'
from pathlib import Path
import yaml
from huggingface_hub import snapshot_download
config = yaml.safe_load(Path('configs/train_qwen_v2.yaml').read_text())
print(snapshot_download(
    repo_id=config['model_id'], revision=config['revision'],
    allow_patterns=['*.json', '*.safetensors', '*.txt', '*.jinja'],
))
PY
printf '\n== Download the bounded dataset, build and evaluate the complete project ==\n'
# The actual dataset download is the first data stage of this tracked workflow.
# A source-only checkout needs no preexisting DVC remote or model artifacts.
./scripts/ta_evaluate.sh "${args[@]}"
printf '\nFresh-checkout setup and TA evaluation completed. Bootstrap log: %s\n' "$bootstrap_log"
