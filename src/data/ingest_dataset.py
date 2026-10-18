"""Bounded streaming ingest. Requires `datasets`; never materialises the full corpus."""
import argparse, json, time
from pathlib import Path
from src.data.common import write_jsonl

def bounded_parquet_rows(dataset, revision, scan_limit, target):
    """Range-read only the first required Parquet row groups; avoids datasets/dill on Python 3.14."""
    if dataset != "AI-MO/NuminaMath-1.5" or not revision:
        raise ValueError("Direct bounded ingest currently requires NuminaMath with an explicit revision")
    import fsspec
    import pyarrow.parquet as pq
    base=f"https://huggingface.co/datasets/{dataset}/resolve/{revision}/data"
    scanned=0
    for shard in range(3):
        url=f"{base}/train-{shard:05d}-of-00003.parquet"
        with fsspec.open(url,"rb",block_size=5*1024*1024).open() as handle:
            for batch in pq.ParquetFile(handle).iter_batches(batch_size=256):
                for row in batch.to_pylist():
                    yield row; scanned += 1
                    if scanned >= scan_limit or scanned >= target: return

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--dataset", default="AI-MO/NuminaMath-1.5"); parser.add_argument("--revision", default=None); parser.add_argument("--scan-limit", type=int, default=4000); parser.add_argument("--target", type=int, default=800); parser.add_argument("--output", default="data/raw/numinamath.jsonl")
    args = parser.parse_args(); started=time.monotonic()
    rows=[]; schema=None
    for scanned, row in enumerate(bounded_parquet_rows(args.dataset,args.revision,args.scan_limit,args.target), 1):
        schema = schema or {k: type(v).__name__ for k,v in row.items()}
        rows.append(dict(row))
        if len(rows) >= args.target or scanned >= args.scan_limit: break
    write_jsonl(rows, args.output)
    Path("reports/eda").mkdir(parents=True, exist_ok=True)
    Path("reports/eda/ingestion.json").write_text(json.dumps({"dataset":args.dataset,"revision":args.revision,"scanned":scanned if rows else 0,"written":len(rows),"schema":schema,"engine":"pyarrow_parquet_range","seconds":time.monotonic()-started},indent=2)+"\n")
if __name__ == "__main__": main()
