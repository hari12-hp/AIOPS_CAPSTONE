# Model Card

## Selected model and purpose

Qwen/Qwen2.5-0.5B-Instruct at revision `7ae557604adf67be50417f59c2c2f167def9a775`, with a locally trained rank-8 LoRA adapter. The intended application is single-user mathematics practice and an AIOps lifecycle demonstration on a CPU. The model provides generated explanations that users should check.

## Training and lineage

Training uses the bounded NuminaMath snapshot described in the data card. Only attention q/k/v/o LoRA parameters are updated. Prompt labels are masked, truncated completions are counted, and one epoch uses float32, batch size 1, accumulation 4, learning rate 0.00005 and seed 42. The evaluation report contains measured counts, loss and duration. DVC records artifacts and dependencies; MLflow records live training metrics, source/environment identity and the registered model version.

## Evaluation

Base and adapter completion loss are compared on the same 73-row held-out test partition. A separate five-question generated-answer smoke suite declares its expected patterns before execution and uses an 80% threshold. The report retains every answer and the adapter hash. Registry promotion verifies that identity and recomputes the saved case decisions. These checks are bounded functionality evidence; neither low loss nor five successful simple answers proves general mathematical correctness.

## Serving behavior

The accepted `champion` alias is loaded by MLflow Models Serve. FastAPI validates questions and calls the registered dataframe signature. Generation is greedy, CPU access is serialized, inputs are limited to 2,048 tokens after request validation, and outputs to 128 new tokens. The UI supports questions of at most 8,000 characters. The model has no calculator, symbolic solver or retrieval tool attached.

## Limits

Long or complex reasoning can fail, incomplete reference solutions are present in the snapshot, and source sampling is concentrated in Olympiad problems. Users should verify numeric results and reasoning. There is no multi-user capacity guarantee or broad independent mathematics benchmark in this submission. The upstream base model and historical comparison resources retain their own notices; see `THIRD_PARTY_NOTICES.md`.
