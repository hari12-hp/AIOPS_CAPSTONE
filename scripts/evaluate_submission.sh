#!/usr/bin/env bash
# Verify local source and evidence; use --full for a fresh generation smoke run.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
case "${1:-}" in ''|--full) ;; *) echo 'Usage: scripts/evaluate_submission.sh [--full]' >&2; exit 2;; esac
if [[ ! -x .venv/bin/python ]]; then echo 'Run scripts/setup.sh first.' >&2; exit 1; fi
.venv/bin/python -m pytest -q --junitxml=reports/test-results.xml
.venv/bin/dvc dag
.venv/bin/dvc status
.venv/bin/python -m src.training.verify_submission
docker compose config -q
.venv/bin/python -m json.tool monitoring/grafana/dashboards/local_math_assistant.json >/dev/null
docker compose run --rm --no-deps --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose run --rm --no-deps --entrypoint promtool prometheus test rules /etc/prometheus/tests/alerts.test.yml /etc/prometheus/tests/recording.test.yml
docker compose run --rm --no-deps --entrypoint amtool alertmanager check-config /etc/alertmanager/alertmanager.yml
if [[ "${1:-}" == '--full' ]]; then
  OMP_NUM_THREADS=4 .venv/bin/python -m src.training.evaluate_generation_benchmark \
    --model Qwen/Qwen2.5-0.5B-Instruct --revision 7ae557604adf67be50417f59c2c2f167def9a775 \
    --adapter models/adapters/qwen-v2 --max-new-tokens 48 \
    --output reports/runtime/qwen_generation_rerun.json
  .venv/bin/python -m src.training.verify_submission --report reports/runtime/qwen_generation_rerun.json
fi
printf '\nLocal submission verification passed.\n'
