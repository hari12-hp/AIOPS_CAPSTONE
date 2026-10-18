"""Audit-friendly, deterministic evaluation report writer (model generation is deliberately separate)."""
import argparse, json, time
from pathlib import Path
from src.data.common import read_jsonl
def main():
    p=argparse.ArgumentParser(); p.add_argument("--test-data",default="data/splits/test.jsonl"); p.add_argument("--candidate",required=True); p.add_argument("--output",default="reports/evaluation/report.json"); a=p.parse_args(); rows=list(read_jsonl(a.test_data)); report={"candidate":a.candidate,"test_examples":len(rows),"status":"not_run","reason":"Generation requires explicitly supplied local base-model weights; no metric is fabricated.","created_at":time.time()}; Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__": main()
