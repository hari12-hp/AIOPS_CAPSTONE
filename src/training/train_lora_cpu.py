"""Explicit CPU-only LoRA trainer. Run preflight/benchmark before `--train`."""
import argparse, json, os, time
from pathlib import Path
from src.data.common import read_jsonl
from src.training.prompting import completion_labels

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--model",required=True); parser.add_argument("--revision"); parser.add_argument("--train-data",default="data/splits/train.jsonl"); parser.add_argument("--output",required=True); parser.add_argument("--max-length",type=int,default=256); parser.add_argument("--threads",type=int,default=6); parser.add_argument("--benchmark-steps",type=int,default=0); parser.add_argument("--benchmark-report",default="reports/runtime/benchmark.json"); parser.add_argument("--max-rss-gib",type=float); parser.add_argument("--epochs",type=float,default=1); parser.add_argument("--learning-rate",type=float,default=5e-5); parser.add_argument("--train",action="store_true"); args=parser.parse_args()
    try:
        import torch; from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments; from peft import LoraConfig,get_peft_model
    except ImportError as exc: raise SystemExit("Install requirements.lock before training: "+str(exc))
    torch.set_num_threads(args.threads); tokenizer=AutoTokenizer.from_pretrained(args.model,revision=args.revision); tokenizer.pad_token=tokenizer.pad_token or tokenizer.eos_token
    model=AutoModelForCausalLM.from_pretrained(args.model,revision=args.revision,dtype=torch.float32,low_cpu_mem_usage=True); model.config.use_cache=False
    targets=[x for x in ("q_proj","k_proj","v_proj","o_proj") if any(n.endswith(x) for n,_ in model.named_modules())]
    if len(targets)!=4: raise SystemExit(f"Unsupported LoRA targets; detected {targets}")
    model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=.05,target_modules=targets,task_type="CAUSAL_LM")); trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)
    if not trainable: raise SystemExit("No trainable adapter parameters")
    rows=list(read_jsonl(args.train_data)); candidate_rows=[completion_labels(tokenizer,[{"role":"system","content":"Solve the mathematics problem carefully."},{"role":"user","content":r["problem"]}],r["solution"],args.max_length) for r in rows]
    encoded=[row for row in candidate_rows if any(value != -100 for value in row["labels"])]
    rejected_fully_truncated=len(candidate_rows)-len(encoded)
    if not encoded: raise SystemExit("Every completion was fully masked/truncated")
    class Rows(torch.utils.data.Dataset):
        def __len__(self): return len(encoded)
        def __getitem__(self,index): return {key:torch.tensor(value) for key,value in encoded[index].items()}
    def collate(rows):
        width=max(len(row["input_ids"]) for row in rows); batch={}
        for key,pad in (("input_ids",tokenizer.pad_token_id),("attention_mask",0),("labels",-100)):
            batch[key]=torch.stack([torch.nn.functional.pad(row[key],(0,width-len(row[key])),value=pad) for row in rows])
        return batch
    preflight={"preflight":"passed","trainable_parameters":trainable,"records":len(encoded),"rejected_fully_truncated":rejected_fully_truncated,"targets":targets}
    if args.benchmark_steps:
        import psutil
        optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=args.learning_rate)
        model.train(); started=time.monotonic(); losses=[]
        for index in range(args.benchmark_steps):
            batch=collate([Rows()[index % len(encoded)]])
            loss=model(**batch).loss
            if not torch.isfinite(loss): raise SystemExit("Non-finite benchmark loss")
            loss.backward(); optimizer.step(); optimizer.zero_grad(); losses.append(float(loss.detach()))
        seconds=time.monotonic()-started
        report={**preflight,"benchmark_steps":args.benchmark_steps,"seconds":seconds,"seconds_per_step":seconds/args.benchmark_steps,"losses":losses,"process_rss_bytes":psutil.Process().memory_info().rss}
        rss_gib=report["process_rss_bytes"] / 1024**3
        report["process_rss_gib"]=rss_gib
        report_path=Path(args.benchmark_report); report_path.parent.mkdir(parents=True,exist_ok=True); report_path.write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report))
        if args.max_rss_gib is not None and rss_gib > args.max_rss_gib:
            raise SystemExit(f"Benchmark RSS {rss_gib:.2f} GiB exceeds approved limit {args.max_rss_gib:.2f} GiB")
        if not args.train: return
    elif not args.train:
        print(json.dumps(preflight)); return
    Path(args.output).mkdir(parents=True,exist_ok=True)
    train_args=TrainingArguments(output_dir=args.output,per_device_train_batch_size=1,gradient_accumulation_steps=4,num_train_epochs=args.epochs,learning_rate=args.learning_rate,optim="adamw_torch",dataloader_num_workers=0,save_strategy="steps",save_steps=50,logging_steps=5,report_to=[],use_cpu=True,fp16=False,bf16=False,remove_unused_columns=False)
    trainer=Trainer(model=model,args=train_args,train_dataset=Rows(),data_collator=collate)
    result=trainer.train(); model.save_pretrained(args.output); tokenizer.save_pretrained(args.output)
    Path(args.output,"training_result.json").write_text(json.dumps({"metrics":result.metrics,"trainable_parameters":trainable,"targets":targets,"rejected_fully_truncated":rejected_fully_truncated},indent=2)+"\n")
if __name__=="__main__": main()
