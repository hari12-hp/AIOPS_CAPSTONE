import hashlib
import json
import re
from pathlib import Path

REQUIRED_FIELDS = ("problem", "solution")


def normalise_question(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def record_id(record: dict) -> str:
    payload = (
        normalise_question(record.get("problem", ""))
        + "\n"
        + (record.get("solution") or "").strip()
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path: str | Path):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(records, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
