# TA setup and evaluation

## Public resources

The fresh-checkout script prints these links before doing any work:

| Resource | Repository | Pinned revision |
|---|---|---|
| Base model and tokenizer | [Qwen/Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) | [7ae557604adf67be50417f59c2c2f167def9a775](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775) |
| Training/evaluation data | [AI-MO/NuminaMath-1.5](https://huggingface.co/datasets/AI-MO/NuminaMath-1.5) | [1b05109f9e5c1ad06c0663519502416c30b300f8](https://huggingface.co/datasets/AI-MO/NuminaMath-1.5/tree/1b05109f9e5c1ad06c0663519502416c30b300f8) |

The scripts download the public Qwen weights and tokenizer into the Hugging Face cache. The DVC ingestion stage range-reads an 800-example dataset snapshot; it does not download the entire NuminaMath corpus. The LoRA adapter is built locally. Historical Gemma evidence remains available in the submission bundle, but Gemma is not a dependency of this rebuild. No Hugging Face account or private model repository is required.

## Machine prerequisites

Use Linux with Bash, Python **3.14.6** including `venv`, Java **17 or newer**, Git, `flock` (util-linux), Docker Engine and the **Compose v2** plugin. Start the Docker daemon and give the current user permission to run Docker. The scripts check these prerequisites and report missing tools; they do not install system packages or change user permissions.

Allow approximately 8 GiB of available memory and 15 GiB of free disk for the environment, model, Docker images and run artifacts. Internet access is required for first-time packages, images and public resources. Training takes about 25–30 minutes on the demonstration CPU; a fresh dependency/image build adds time and slower machines take longer. Stop other memory-heavy tasks before training.

If needed, choose the interpreter/cache explicitly:

```bash
export PYTHON_BIN=/absolute/path/to/python3.14
export JAVA_HOME=/absolute/path/to/jdk-17
export MATH_ASSISTANT_HF_CACHE=/absolute/path/to/huggingface
```

A project-local `.tools/java17` is automatically detected when present. Model downloads and Docker serving use the same cache path. Run the scripts from a terminal; they locate the project root themselves.

## Script 1: evaluate the entire workflow

```bash
./scripts/ta_evaluate.sh
```

Use this after setup when `.venv` already contains the pinned dependencies and the base model is cached. The script performs the following sequence and stops on the first failure:

1. Check the Python environment and Compose configuration. Acquire a checkout-local evaluation lock and create an individual log.
2. Stop the project's nine services to free training memory, preserving artifacts and volumes.
3. Force the complete DVC graph: environment inspection, dataset ingestion, EDA, Spark cleaning, splitting, CPU benchmark, LoRA training, base evaluation, adapter evaluation, generated-answer acceptance and registry promotion.
4. Ensure a local executable champion exists, restoring registration from verified artifacts only if needed. Update the console's links to the actual local MLflow experiment ID.
5. Run unit tests, display the DVC graph/status, validate submitted acceptance evidence, check Compose/Grafana configuration, regenerate the five-question smoke suite into a separate runtime file, and exercise the MLprojects test entry point.
6. Build the backend/frontend Docker images and recreate all nine services. Recreating model serving loads the current champion.
7. Verify real web/API-to-model inference, MLflow, exporter metrics, Prometheus targets, the provisioned Grafana dashboard, data separation and the completed pipeline. Check that the separate pipeline console responds, then verify the three dashboards, all fifteen scrape targets, eight HTTP probes and recent real Watchdog delivery.
8. Print service health, local links and the pass-result file. Leave the application running for inspection or recording.

Options can be combined:

```bash
# Display the sequence without downloads, changes, training or service operations
./scripts/ta_evaluate.sh --dry-run

# Allow DVC to reuse unchanged outputs; rerun missing or changed stages
./scripts/ta_evaluate.sh --cached

# Use existing Docker images for a faster review on the demonstration machine
./scripts/ta_evaluate.sh --cached --skip-build
```

`--cached` can still train if outputs or dependencies changed. `--skip-build` requires current images; it is not a fresh-machine setup. The default always retrains and builds. Acceptance checks report a five-case functional smoke score, not broad mathematical accuracy.

## Script 2: build a fresh checkout with one command

```bash
./scripts/bootstrap_project.sh
```

This script prints the pinned model and dataset links, checks machine prerequisites, creates `.venv`, installs `requirements.lock`, downloads the pinned base model/tokenizer, then invokes Script 1. The ingestion stage downloads the bounded dataset, and the rest of the tracked workflow builds the adapter, registration, images and running application. A source-only checkout needs neither the demonstration machine's MLflow database nor its ignored DVC artifact store. An unpacked ZIP without `.git` gets a local Git repository for DVC; the script makes no commits.

For a preview or a repeat setup:

```bash
./scripts/bootstrap_project.sh --dry-run
./scripts/bootstrap_project.sh --cached
```

The selected pipeline rebuilds Qwen outputs; it does not fetch missing historical Gemma artifacts. `dvc status` may list those standalone historical artifacts as missing in a source-only clone. They are outside the selected rebuild graph and are not used by the deployed model.

## Results and local screens

Each evaluation creates `reports/runtime/ta-evaluation-<UTC timestamp>-<PID>.log` and a matching JSON result with `passed` or `failed`, the last phase and completed steps. Bootstrap adds a `bootstrap-<UTC timestamp>-<PID>.log`. Failures return a nonzero exit code; a failed pipeline prevents startup and a failed runtime check prevents a pass result. Preflight errors print directly before a run log is created.

Detailed pipeline output is in `reports/runtime/pipeline.log`. MLflow stores parent/stage runs and artifacts in the checkout's SQLite-backed tracking store. Unit results are in `reports/test-results.xml`; fresh smoke results are in `reports/runtime/qwen_generation_rerun.json`; live checks are in `reports/runtime/runtime-verification.json`. Cached stages retain their earlier evidence rather than acquiring invented new measurements.

| Screen | Local URL |
|---|---|
| Math workspace | http://localhost:8080/ |
| Pipeline console | http://localhost:8081/ |
| MLflow experiments and registry | http://localhost:5000/ |
| FastAPI documentation | http://localhost:8000/docs |
| MLflow model health | http://localhost:5002/ping |
| Prometheus | http://localhost:19090/ |
| Grafana operations | http://localhost:13000/d/local-math-assistant |
| Grafana Alert Center | http://localhost:13000/d/math-alert-center |
| Grafana ML lifecycle | http://localhost:13000/d/math-mlops |
| Alertmanager and silences | http://localhost:19093/ |
| Local alert inbox | http://localhost:19199/ |

On failure, inspect the reported phase and log, then use `docker compose logs model-serving backend` if startup/inference failed. Services remain in their last state for diagnosis; a failure after the stop step may leave them stopped. Fix the reported issue and rerun, using `--cached` when appropriate. Stop the stack with `docker compose stop` after evaluation.

Both orchestration scripts work locally, preserve prior MLflow runs, and perform no Git commit, GitHub push, cloud deployment or artifact upload.
