"""Auditable CPU generation benchmark with predeclared exact-answer patterns."""

import argparse
import json
from src.training.generation_contract import SYSTEM_PROMPT
import re
import time
from pathlib import Path
from src.training.model_metadata import file_sha256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--benchmark", default="configs/generation_benchmark.json")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--minimum-accuracy", type=float, default=0.8)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    import torch

    torch.set_num_threads(4)
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cases = json.loads(Path(args.benchmark).read_text())
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        args.model, revision=args.revision, dtype=torch.float32, low_cpu_mem_usage=True
    )
    model = PeftModel.from_pretrained(base, args.adapter)
    model.eval()
    results = []
    started = time.monotonic()
    with torch.inference_mode():
        for case in cases:
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {"role": "user", "content": case["question"]},
            ]
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            encoded = tokenizer(prompt, return_tensors="pt")
            generated = model.generate(
                **encoded, max_new_tokens=args.max_new_tokens, do_sample=False
            )
            answer = tokenizer.decode(
                generated[0][encoded["input_ids"].shape[1] :], skip_special_tokens=True
            ).strip()
            passed = any(re.search(pattern, answer) for pattern in case["accepted_patterns"])
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "accepted_patterns": case["accepted_patterns"],
                    "answer": answer,
                    "passed": passed,
                }
            )
    accuracy = sum(result["passed"] for result in results) / len(results) if results else 0.0
    report = {
        "protocol": "predeclared exact-answer regex acceptance; deterministic greedy CPU generation",
        "model": args.model,
        "requested_revision": args.revision,
        "resolved_revision": getattr(model.config, "_commit_hash", None),
        "adapter": args.adapter,
        "adapter_sha256": file_sha256(Path(args.adapter) / "adapter_model.safetensors"),
        "cases": results,
        "accuracy": accuracy,
        "minimum_accuracy": args.minimum_accuracy,
        "seconds": time.monotonic() - started,
        "status": "accepted" if accuracy >= args.minimum_accuracy else "needs_review",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {key: report[key] for key in ("accuracy", "minimum_accuracy", "seconds", "status")}
        )
    )


if __name__ == "__main__":
    main()
