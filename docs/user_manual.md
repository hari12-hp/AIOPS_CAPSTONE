# User Manual

1. Start the stack: `docker compose up --build`.
2. Open `http://localhost:8080` for the static user interface, or `http://localhost:8000/docs` for the API contract.
3. The UI always displays service and pipeline status. To enable solving, set the three backend environment variables in `.env`: `MATH_ASSISTANT_BASE_MODEL`, `MATH_ASSISTANT_BASE_REVISION`, and `MATH_ASSISTANT_ADAPTER_PATH`.
4. Enter one mathematics question and select **Solve**. The answer panel reports the response and latency. A configuration warning means no model was loaded; it is not a generated answer.
5. Inspect metrics at `http://localhost:9090` and Grafana at `http://localhost:3000`.

Never enter Hugging Face tokens in the UI. Authenticate the local training environment through `hf auth login`.
