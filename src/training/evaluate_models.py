"""Sequential, CPU-safe held-out evaluation for a base model or one LoRA adapter."""

import argparse, json, time
from pathlib import Path
from src.data.common import read_jsonl
from src.training.prompting import completion_labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--adapter")
    parser.add_argument("--test-data", default="data/splits/test.jsonl")
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    import torch

    torch.set_num_threads(4)
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, revision=args.revision, dtype=torch.float32, low_cpu_mem_usage=True
    )
    if args.adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    losses = []
    rejected = 0
    started = time.monotonic()
    rows = list(read_jsonl(args.test_data))[: args.limit]
    with torch.no_grad():
        for row in rows:
            item = completion_labels(
                tokenizer,
                [
                    {"role": "system", "content": "Solve the mathematics problem carefully."},
                    {"role": "user", "content": row["problem"]},
                ],
                row["solution"],
                args.max_length,
            )
            if not any(x != -100 for x in item["labels"]):
                rejected += 1
                continue
            tensors = {key: torch.tensor([value]) for key, value in item.items()}
            losses.append(float(model(**tensors).loss))
    elapsed = time.monotonic() - started
    report = {
        "candidate": "adapter" if args.adapter else "base",
        "model": args.model,
        "revision": args.revision,
        "adapter": args.adapter,
        "test_input_count": len(rows),
        "scored": len(losses),
        "rejected_fully_truncated": rejected,
        "mean_completion_loss": sum(losses) / len(losses) if losses else None,
        "seconds": elapsed,
        "seconds_per_scored": elapsed / len(losses) if losses else None,
        "status": "completed" if losses else "needs_review",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
