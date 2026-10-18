import json
from pathlib import Path
def test_pilot_adapter_has_expected_lora_shape():
    config=json.loads(Path("artifacts/input/pilot-v1/adapter_config.json").read_text())
    assert config["r"]==8 and config["lora_alpha"]==16
    assert set(config["target_modules"])=={"q_proj","k_proj","v_proj","o_proj"}
