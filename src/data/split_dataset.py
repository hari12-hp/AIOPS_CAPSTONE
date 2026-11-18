import argparse, glob, hashlib, json
from pathlib import Path
from src.data.common import read_jsonl, write_jsonl, normalise_question, sha256


def bucket(question, seed):
    return (
        int(hashlib.sha256(f"{seed}:{normalise_question(question)}".encode()).hexdigest(), 16) % 100
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--outdir", default="data/splits")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    groups = {"train": [], "validation": [], "test": []}
    inputs = sorted(glob.glob(args.input))
    if not inputs:
        raise SystemExit(f"No input files match: {args.input}")
    seen = set()
    for path in inputs:
        for row in read_jsonl(path):
            key = normalise_question(row.get("problem", ""))
            if key in seen:
                continue
            seen.add(key)
            value = bucket(key, args.seed)
            groups["train" if value < 80 else "validation" if value < 90 else "test"].append(row)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in groups.items():
        rows.sort(key=lambda row: normalise_question(row["problem"]))
        write_jsonl(rows, out / f"{name}.jsonl")
    report = {
        name: {"count": len(rows), "sha256": sha256(out / f"{name}.jsonl")}
        for name, rows in groups.items()
    }
    Path("reports/eda/splits.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
