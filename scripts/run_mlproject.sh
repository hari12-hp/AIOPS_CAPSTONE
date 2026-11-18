#!/usr/bin/env bash
# MLprojects --env-manager local uses the active interpreter's PATH.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source .venv/bin/activate
export MLFLOW_TRACKING_URI="sqlite:///$PWD/mlflow.db"
mlflow run . -e "${1:-test}" --env-manager local
