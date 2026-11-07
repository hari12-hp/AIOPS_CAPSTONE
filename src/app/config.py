from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    root: Path = Path(__file__).resolve().parents[2]
    base_model: str = os.getenv("MATH_ASSISTANT_BASE_MODEL", "")
    base_revision: str | None = os.getenv("MATH_ASSISTANT_BASE_REVISION") or None
    adapter_path: str | None = os.getenv("MATH_ASSISTANT_ADAPTER_PATH") or None
    max_new_tokens: int = int(os.getenv("MATH_ASSISTANT_MAX_NEW_TOKENS", "128"))

settings = Settings()
