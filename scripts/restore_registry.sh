#!/usr/bin/env bash
# Rebuild portable MLflow registration from DVC-restored adapters and evaluations.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
.venv/bin/python -m src.training.register_model \
  --model Qwen/Qwen2.5-0.5B-Instruct --revision 7ae557604adf67be50417f59c2c2f167def9a775 \
  --adapter models/adapters/qwen-v2 --evaluation reports/evaluation/qwen_lora_v2.json \
  --acceptance reports/evaluation/qwen_v2_generation.json \
  --name local-math-assistant-qwen-cpu-v2 --output reports/runtime/restored_registration.json
