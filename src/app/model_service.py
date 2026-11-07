"""Lazy, single-model inference service; no model is loaded at import or startup."""
import logging
from threading import Lock
from time import perf_counter
from .config import Settings

LOGGER = logging.getLogger(__name__)

class ModelUnavailable(RuntimeError):
    pass

class ModelService:
    def __init__(self, config: Settings):
        self.config=config; self._lock=Lock(); self._model=None; self._tokenizer=None

    @property
    def ready(self): return self._model is not None

    def _load(self):
        if self._model is not None: return
        if not self.config.base_model or not self.config.adapter_path:
            raise ModelUnavailable("Set MATH_ASSISTANT_BASE_MODEL and MATH_ASSISTANT_ADAPTER_PATH before requesting inference.")
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        started=perf_counter()
        tokenizer=AutoTokenizer.from_pretrained(self.config.base_model, revision=self.config.base_revision)
        tokenizer.pad_token=tokenizer.pad_token or tokenizer.eos_token
        base=AutoModelForCausalLM.from_pretrained(self.config.base_model, revision=self.config.base_revision,torch_dtype=torch.float32,low_cpu_mem_usage=True)
        self._model=PeftModel.from_pretrained(base,self.config.adapter_path); self._model.eval(); self._tokenizer=tokenizer
        LOGGER.info("model_loaded model=%s revision=%s seconds=%.3f", self.config.base_model, self.config.base_revision, perf_counter()-started)

    def solve(self, question: str) -> tuple[str, float]:
        with self._lock:
            self._load(); started=perf_counter()
            messages=[{"role":"system","content":"Solve the mathematics problem carefully. Show concise reasoning and a final answer."},{"role":"user","content":question}]
            prompt=self._tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            inputs=self._tokenizer(prompt,return_tensors="pt")
            with torch.inference_mode():
                output=self._model.generate(**inputs,max_new_tokens=self.config.max_new_tokens,do_sample=False)
            completion=output[0][inputs["input_ids"].shape[1]:]
            return self._tokenizer.decode(completion,skip_special_tokens=True), perf_counter()-started
