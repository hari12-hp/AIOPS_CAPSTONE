"""Register an executable MLflow pyfunc with verified acceptance and lineage."""

import argparse
import json
from src.training.generation_contract import SYSTEM_PROMPT, decode_answer
import os
import time
from pathlib import Path
from threading import Lock
import mlflow.pyfunc

from src.training.verify_submission import validate_report
from src.training.model_metadata import git_metadata, file_sha256


class AdapterPyfunc(mlflow.pyfunc.PythonModel):
    """The same instruction contract is used by MLflow serving and the web API."""

    def load_context(self, context):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        torch.set_num_threads(4)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
        self.tokenizer.pad_token = self.tokenizer.pad_token or self.tokenizer.eos_token
        base = AutoModelForCausalLM.from_pretrained(
            self.model_id, revision=self.revision, dtype=torch.float32, low_cpu_mem_usage=True
        )
        self.model = PeftModel.from_pretrained(base, context.artifacts["adapter"])
        self.model.eval()
        self.lock = Lock()
        # The model process has its own exporter; the web API measures REST overhead.
        from prometheus_client import Counter, Histogram, Gauge, start_http_server

        self.requests = Counter("math_model_predictions_total", "Generated answers")
        self.duration = Histogram(
            "math_model_generation_seconds", "Per-question generation latency"
        )
        Gauge("math_model_loaded", "Registered adapter loaded").set(1)
        port = os.getenv("MATH_ASSISTANT_EXPORTER_PORT")
        if port:
            start_http_server(int(port))

    def predict(self, context, model_input, params=None):
        import torch

        prompts = model_input["prompt"].tolist()
        answers = []
        with self.lock, torch.inference_mode():
            for question in prompts:
                started = time.perf_counter()
                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": question},
                ]
                text = self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                encoded = self.tokenizer(
                    text, return_tensors="pt", truncation=True, max_length=2048
                )
                generated = self.model.generate(**encoded, max_new_tokens=128, do_sample=False)
                answers.append(
                    decode_answer(
                        self.tokenizer, generated[0][encoded["input_ids"].shape[1] :], 128
                    )
                )
                self.requests.inc()
                self.duration.observe(time.perf_counter() - started)
        return answers


def main():
    parser = argparse.ArgumentParser()
    for name in ("adapter", "model", "revision", "evaluation", "acceptance", "name", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    import mlflow
    from mlflow.models import ModelSignature
    from mlflow.types import Schema, ColSpec
    from mlflow.tracking import MlflowClient

    root = Path.cwd()
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{root / 'mlflow.db'}"))
    mlflow.set_experiment("mathematics-pipeline")
    evaluation = json.loads(Path(args.evaluation).read_text())
    acceptance = json.loads(Path(args.acceptance).read_text())
    decision = validate_report(acceptance)
    if (
        acceptance.get("model") != args.model
        or acceptance.get("requested_revision") != args.revision
    ):
        raise SystemExit("Acceptance evidence belongs to a different base model revision")
    adapter = Path(args.adapter)
    weights_hash = file_sha256(adapter / "adapter_model.safetensors")
    if acceptance.get("adapter_sha256") != weights_hash:
        raise SystemExit("Acceptance evidence does not match these adapter weights")
    wrapper = AdapterPyfunc()
    wrapper.model_id, wrapper.revision = args.model, args.revision
    run_id = os.getenv("MLFLOW_RUN_ID")
    with (
        mlflow.start_run(run_id=run_id) if run_id else mlflow.start_run(run_name="register") as run
    ):
        mlflow.log_params(
            {
                "base_model": args.model,
                "base_revision": args.revision,
                "adapter_sha256": weights_hash,
                **git_metadata(),
            }
        )
        mlflow.log_metrics(
            {
                "test_completion_loss": evaluation["mean_completion_loss"],
                "generation_accuracy": decision["accuracy"],
            }
        )
        signature = ModelSignature(
            inputs=Schema([ColSpec("string", "prompt")]), outputs=Schema([ColSpec("string")])
        )
        info = mlflow.pyfunc.log_model(
            name="model",
            python_model=wrapper,
            artifacts={"adapter": str(adapter.resolve())},
            code_paths=[str(root / "src")],
            signature=signature,
            pip_requirements=[
                "transformers==4.57.1",
                "peft==0.17.1",
                "torch==2.14.1+cpu",
                "mlflow==3.15.1",
            ],
        )
        client = MlflowClient()
        from mlflow.exceptions import MlflowException

        try:
            client.create_registered_model(args.name)
        except MlflowException as exc:
            if exc.error_code != "RESOURCE_ALREADY_EXISTS":
                raise
        version = client.create_model_version(args.name, info.model_uri, run.info.run_id)
        status = "accepted" if decision["accepted"] else "needs_review"
        client.set_model_version_tag(args.name, version.version, "validation_status", status)
        client.set_model_version_tag(args.name, version.version, "adapter_sha256", weights_hash)
        client.set_model_version_tag(
            args.name, version.version, "generation_accuracy", str(decision["accuracy"])
        )
        if decision["accepted"]:
            client.set_registered_model_alias(args.name, "champion", version.version)
        mlflow.set_tag("validation_status", status)
        output = {
            "run_id": run.info.run_id,
            "model_name": args.name,
            "version": version.version,
            "model_uri": info.model_uri,
            "validation_status": status,
            "adapter_sha256": weights_hash,
            **decision,
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps(output))
        if not decision["accepted"]:
            raise SystemExit("Candidate registered for review; champion was not changed")


if __name__ == "__main__":
    main()
