import hashlib, json, subprocess
from pathlib import Path
def file_sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()
def git_metadata(root="."):
    try:
        commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True,stderr=subprocess.DEVNULL).strip(); dirty=bool(subprocess.check_output(["git","status","--porcelain"],cwd=root,text=True).strip()); return {"git_commit":commit,"git_dirty":dirty}
    except Exception: return {"git_commit":None,"git_dirty":None}
def write_metadata(adapter_dir, base_model, revision, output):
    p=Path(adapter_dir); report={**git_metadata(),"base_model":base_model,"base_revision":revision,"adapter_files":{x.name:file_sha256(x) for x in p.iterdir() if x.is_file()}}; Path(output).write_text(json.dumps(report,indent=2)+"\n"); return report
