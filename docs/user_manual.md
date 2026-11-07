# User Manual

1. Start the stack: `docker compose up --build`.
2. Open `http://localhost:8080` for the static user interface, or `http://localhost:8000/docs` for the API contract.
3. The Compose defaults select the accepted CPU candidate: Qwen 2.5 0.5B at revision `7ae557604adf67be50417f59c2c2f167def9a775` with the read-only mounted Qwen V2 adapter. Override `MATH_ASSISTANT_BASE_MODEL`, `MATH_ASSISTANT_BASE_REVISION`, or `MATH_ASSISTANT_ADAPTER_PATH` in `.env` only when deliberately testing another registered candidate.

For a fast first inference on a machine that already has the base model, set `MATH_ASSISTANT_HF_CACHE` to its Hugging Face cache directory before starting Compose. Otherwise Compose persists a new download under `.hf-cache`.
4. Enter one mathematics question and select **Solve**. The answer panel reports the response and latency. A configuration warning means no model was loaded; it is not a generated answer.
5. Inspect metrics at `http://localhost:9090` and Grafana at `http://localhost:3000`.
6. For quality evidence, review `docs/evaluation_report.md` and the DVC-tracked `reports/evaluation/qwen_v2_generation.json`. The current benchmark is a small acceptance suite, not a promise that every math question will be correct.

Never enter Hugging Face tokens in the UI. Authenticate the local training environment through `hf auth login`.

## Evaluator shortcut

Run `./scripts/evaluate_submission.sh` from the repository root for the non-interactive validation sequence. Add `--full` to rerun the Qwen generated-answer acceptance gate. The script does not build or start containers; after it passes, use `docker compose up --build` to demonstrate the UI and monitoring stack.
