"""Inference boundary: MLflow serving in Compose, lazy local inference otherwise."""

import json
from src.training.generation_contract import SYSTEM_PROMPT, decode_answer
import logging
from threading import Lock
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Settings

LOGGER = logging.getLogger(__name__)


class ModelUnavailable(RuntimeError):
    """The selected inference engine cannot currently answer requests."""


class ModelService:
    def __init__(self, config: Settings):
        self.config = config
        self._lock = Lock()
        self._model = None
        self._tokenizer = None
        self._remote_ready = False

    @property
    def ready(self):
        return self._remote_ready if self.config.serving_url else self._model is not None

    def _load(self):
        if self._model is not None:
            return
        if not self.config.base_model or not self.config.adapter_path:
            raise ModelUnavailable(
                "The model is not configured. Ask the operator to start the local model service."
            )
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        torch.set_num_threads(self.config.cpu_threads)
        started = perf_counter()
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.config.base_model, revision=self.config.base_revision
            )
            tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
            base = AutoModelForCausalLM.from_pretrained(
                self.config.base_model,
                revision=self.config.base_revision,
                dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            model = PeftModel.from_pretrained(base, self.config.adapter_path)
            model.eval()
        except (OSError, ValueError) as exc:
            LOGGER.exception("model_load_failed")
            raise ModelUnavailable(
                "The local model could not be loaded. Check the model files and server logs."
            ) from exc
        # Publish both objects only after loading completes successfully.
        self._model, self._tokenizer = model, tokenizer
        LOGGER.info(
            "model_loaded model=%s revision=%s seconds=%.3f",
            self.config.base_model,
            self.config.base_revision,
            perf_counter() - started,
        )

    def solve(self, question: str) -> tuple[str, float]:
        with self._lock:
            started = perf_counter()
            if self.config.serving_url:
                request = Request(
                    self.config.serving_url.rstrip("/") + "/invocations",
                    data=json.dumps(
                        {"dataframe_split": {"columns": ["prompt"], "data": [[question]]}}
                    ).encode(),
                    headers={"Content-Type": "application/json"},
                )
                try:
                    with urlopen(request, timeout=180) as response:
                        answer = json.load(response)["predictions"][0]
                    if not isinstance(answer, str) or not answer.strip():
                        raise ValueError("Empty inference response")
                except (
                    HTTPError,
                    URLError,
                    TimeoutError,
                    OSError,
                    ValueError,
                    KeyError,
                    IndexError,
                ) as exc:
                    self._remote_ready = False
                    LOGGER.warning("model_server_unavailable error_type=%s", type(exc).__name__)
                    raise ModelUnavailable(
                        "The model service is starting or unavailable. Try again shortly."
                    ) from exc
                self._remote_ready = True
                return answer, perf_counter() - started
            self._load()
            import torch

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {"role": "user", "content": question},
            ]
            prompt = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
            with torch.inference_mode():
                output = self._model.generate(
                    **inputs, max_new_tokens=self.config.max_new_tokens, do_sample=False
                )
            completion = output[0][inputs["input_ids"].shape[1] :]
            return decode_answer(
                self._tokenizer, completion, self.config.max_new_tokens
            ), perf_counter() - started
