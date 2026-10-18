"""Environment and local-artifact inspection; no dataset download."""
import json, os, platform, shutil, subprocess
from pathlib import Path
from src.data.common import sha256

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "artifacts/input/pilot-v1"

def git_value(*args):
    try: return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception: return None

def main():
    available = shutil.disk_usage(ROOT).free
    report = {"python": platform.python_version(), "platform": platform.platform(),
              "cpu_count_logical": os.cpu_count(), "disk_free_bytes": available,
              "git_commit": git_value("rev-parse", "HEAD"),
              "git_dirty": None, "pilot": {}}
    for name in ("pilot_manifest.json", "base_vs_lora_comparison.csv", "adapter_config.json", "adapter_model.safetensors"):
        path = PILOT / name
        report["pilot"][name] = {"present": path.exists(), **({"sha256": sha256(path), "bytes": path.stat().st_size} if path.exists() else {})}
    try: report["git_dirty"] = bool(git_value("status", "--porcelain"))
    except Exception: pass
    destination = ROOT / "reports/runtime/environment.json"; destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
if __name__ == "__main__": main()
