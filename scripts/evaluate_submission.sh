#!/usr/bin/env bash
# One-command evaluator for the submitted local Mathematics Assistant.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FULL_MODE=false

if [[ "${1:-}" == "--full" ]]; then
  FULL_MODE=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--full]" >&2
  exit 2
fi

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing project environment: create .venv and install requirements.lock first." >&2
  exit 1
fi

cd "$ROOT_DIR"
source .venv/bin/activate

echo "==> Restoring DVC-tracked submission artifacts"
dvc pull -q

echo "==> Running unit and contract tests"
python -m pytest -q

echo "==> Checking DVC graph state"
dvc status

echo "==> Validating deployment and dashboard configuration"
docker compose config >/tmp/local-math-assistant-compose.yml
python -m json.tool monitoring/grafana/dashboards/local_math_assistant.json >/dev/null

echo "==> Verifying saved Qwen V2 acceptance evidence"
python -m src.training.verify_submission

if [[ "$FULL_MODE" == true ]]; then
  echo "==> Re-running deterministic Qwen V2 generated-answer gate"
  RERUN_REPORT="reports/runtime/qwen_v2_generation_rerun.json"
  python -m src.training.evaluate_generation_benchmark \
    --model Qwen/Qwen2.5-0.5B-Instruct \
    --revision 7ae557604adf67be50417f59c2c2f167def9a775 \
    --adapter models/adapters/qwen-v2 \
    --benchmark configs/generation_benchmark.json \
    --max-new-tokens 48 \
    --minimum-accuracy 0.8 \
    --output "$RERUN_REPORT"
  python -m src.training.verify_submission --report "$RERUN_REPORT"
fi

echo ""
echo "Submission evaluation passed."
echo "UI: http://localhost:8080 (after: docker compose up --build)"
echo "Evidence: docs/evaluation_report.md"
