#!/usr/bin/env bash
# Install the pinned environment and restore the submission's local DVC artifacts.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git init --quiet; fi
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
if [[ -d .dvc/cache-store ]]; then
  .venv/bin/dvc pull
else
  echo 'No bundled artifact store. Use the submission ZIP, or run the full pipeline to rebuild Qwen.'
fi
printf '\nFor Spark, install Java 17+ and set JAVA_HOME.\n'
printf 'For a full rebuild: .venv/bin/python -m src.pipeline.run --force\n'
printf 'For restored artifacts: ./scripts/restore_registry.sh\n'
