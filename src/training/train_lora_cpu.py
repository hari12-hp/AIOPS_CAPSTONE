"""Explicit CPU-only LoRA trainer. Run preflight/benchmark before `--train`."""
import argparse, json, os, time
from pathlib import Path
from src.data.common import read_jsonl
from src.training.prompting import completion_labels

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--model",required=True); parser.add_argument("--revision"); parser.add_argument("--train-data",default="data/splits/train.jsonl"); parser.add_argument("--output",required=True); parser.add_argument("--max-length",type=int,default=256); parser.add_argument("--threads",type=int,default=6); parser.add_argument("--benchmark-steps",type=int,default=0); parser.add_argument("--epochs",type=float,default=1); parser.add_argument("--learning-rate",type=float,default=5e-5); parser.add_argument("--train",action="store_true"); args=parser.parse_args()
    try:
        import torch; from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments; from peft import LoraConfig,get_peft_model
    except ImportError as exc: raise SystemExit("Install requirements.lock before training: "+str(exc))
    torch.set_num_threads(args.threads); tokenizer=AutoTokenizer.from_pretrained(args.model,revision=args.revision); tokenizer.pad_token=tokenizer.pad_token or tokenizer.eos_token
    model=AutoModelForCausalLM.from_pretrained(args.model,revision=args.revision,torch_dtype=torch.float32,low_cpu_mem_usage=True); model.config.use_cache=False
    targets=[x for x in ("q_proj","k_proj","v_proj","o_proj") if any(n.endswith(x) for n,_ in model.named_modules())]
    if len(targets)!=4: raise SystemExit(f"Unsupported LoRA targets; detected {targets}")
    model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=.05,target_modules=targets,task_type="CAUSAL_LM")); trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)
    if not trainable: raise SystemExit("No trainable adapter parameters")
    rows=list(read_jsonl(args.train_data)); encoded=[completion_labels(tokenizer,[{"role":"system","content":"Solve the mathematics problem carefully."},{"role":"user","content":r["problem"]}],r["solution"],args.max_length) for r in rows]
    if any(not any(v!=-100 for v in r["labels"]) for r in encoded): raise SystemExit("A completion was fully masked/truncated")
    if not args.train: print(json.dumps({"preflight":"passed","trainable_parameters":trainable,"records":len(encoded),"targets":targets})); return
    class Rows(torch.utils.data.Dataset):
        def __len__(self): return len(encoded)
        def __getitem__(self,index): return {key:torch.tensor(value) for key,value in encoded[index].items()}
    def collate(rows):
        width=max(len(row["input_ids"]) for row in rows); batch={}
        for key,pad in (("input_ids",tokenizer.pad_token_id),("attention_mask",0),("labels",-100)):
            batch[key]=torch.stack([torch.nn.functional.pad(row[key],(0,width-len(row[key])),value=pad) for row in rows])
        return batch
    Path(args.output).mkdir(parents=True,exist_ok=True)
    train_args=TrainingArguments(output_dir=args.output,per_device_train_batch_size=1,gradient_accumulation_steps=4,num_train_epochs=args.epochs,learning_rate=args.learning_rate,optim="adamw_torch",dataloader_num_workers=0,save_strategy="steps",save_steps=50,logging_steps=5,report_to=[],use_cpu=True,fp16=False,bf16=False,remove_unused_columns=False)
    trainer=Trainer(model=model,args=train_args,train_dataset=Rows(),data_collator=collate)
    result=trainer.train(); model.save_pretrained(args.output); tokenizer.save_pretrained(args.output)
    Path(args.output,"training_result.json").write_text(json.dumps({"metrics":result.metrics,"trainable_parameters":trainable,"targets":targets},indent=2)+"\n")
if __name__=="__main__": main()
