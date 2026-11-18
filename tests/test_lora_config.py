"""Validate the selected model's public training configuration without weights."""

from pathlib import Path
import yaml


def test_selected_adapter_has_expected_lora_shape():
    config = yaml.safe_load(Path("configs/train_qwen_v2.yaml").read_text())
    assert config["lora"]["r"] == 8
    assert config["lora"]["alpha"] == 16
    assert set(config["target_modules"]) == {"q_proj", "k_proj", "v_proj", "o_proj"}
