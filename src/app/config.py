"""Configuration shared by the independent REST boundary and model service."""

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    root: Path = Path(os.getenv("MATH_ASSISTANT_ROOT", Path(__file__).resolve().parents[2]))
    base_model: str = os.getenv("MATH_ASSISTANT_BASE_MODEL", "")
    base_revision: str | None = os.getenv("MATH_ASSISTANT_BASE_REVISION") or None
    adapter_path: str | None = os.getenv("MATH_ASSISTANT_ADAPTER_PATH") or None
    serving_url: str | None = os.getenv("MATH_ASSISTANT_SERVING_URL") or None
    max_new_tokens: int = int(os.getenv("MATH_ASSISTANT_MAX_NEW_TOKENS", "128"))
    cpu_threads: int = int(os.getenv("MATH_ASSISTANT_CPU_THREADS", "4"))


settings = Settings()
