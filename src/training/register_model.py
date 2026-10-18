"""Log a LoRA adapter as a loadable local MLflow pyfunc model and register it."""
import argparse, json
from pathlib import Path
import mlflow.pyfunc

class AdapterPyfunc(mlflow.pyfunc.PythonModel):
    """Lazy loader keeps base weights out of the registered adapter artifact."""
    def load_context(self, context):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        self.tokenizer=AutoTokenizer.from_pretrained(self.model_id,revision=self.revision)
        self.model=PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(self.model_id,revision=self.revision),context.artifacts["adapter"])
    def predict(self, context, model_input, params=None):
        prompts=model_input["prompt"].tolist() if hasattr(model_input,"__getitem__") else list(model_input)
        encoded=self.tokenizer(prompts,return_tensors="pt",padding=True)
        generated=self.model.generate(**encoded,max_new_tokens=64,do_sample=False)
        return [self.tokenizer.decode(row,skip_special_tokens=True) for row in generated]

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--adapter",required=True); parser.add_argument("--model",required=True); parser.add_argument("--revision"); parser.add_argument("--name",default="local-math-assistant-qwen-cpu-v2"); args=parser.parse_args()
    import mlflow
    from mlflow.tracking import MlflowClient
    root=Path.cwd(); mlflow.set_tracking_uri(f"sqlite:///{root/'mlflow.db'}"); mlflow.set_experiment("local-math-assistant-cpu-training")
    evaluation=json.loads((root/"reports/evaluation/qwen_lora_v2.json").read_text()); training=json.loads((Path(args.adapter)/"training_result.json").read_text())
    wrapper=AdapterPyfunc(); wrapper.model_id=args.model; wrapper.revision=args.revision
    with mlflow.start_run(run_name="qwen-cpu-v2-train-evaluate-register") as run:
        mlflow.log_params({"base_model":args.model,"base_revision":args.revision or "unresolved","lora_r":8,"lora_alpha":16,"lora_dropout":0.05,"train_examples":642,"validation_examples":83,"test_examples":73,"dtype":"float32","cpu_threads":6})
        mlflow.log_metrics({"train_loss":training["metrics"]["train_loss"],"test_completion_loss":evaluation["mean_completion_loss"],"training_seconds":training["metrics"]["train_runtime"]})
        mlflow.set_tags({"validation_status":"needs_review","reason":"No independent generation benchmark or acceptance threshold has been completed","base_model_revision_status":"unresolved"})
        info=mlflow.pyfunc.log_model("model",python_model=wrapper,artifacts={"adapter":str(Path(args.adapter).resolve())},pip_requirements=["transformers==4.57.1","peft==0.17.1","torch==2.14.1+cpu"])
        client=MlflowClient();
        try: client.create_registered_model(args.name)
        except Exception: pass
        version=client.create_model_version(args.name,info.model_uri,run.info.run_id)
        print(json.dumps({"run_id":run.info.run_id,"model_name":args.name,"version":version.version,"model_uri":info.model_uri,"validation_status":"needs_review"}))
if __name__=="__main__": main()
