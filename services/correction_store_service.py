import json
from datetime import datetime
from pathlib import Path

from config import PROJECT_ROOT


CORRECTION_STORE_PATH = PROJECT_ROOT / "data" / "chunk_corrections.json"


def load_chunk_corrections():
    if not CORRECTION_STORE_PATH.exists():
        return {}

    try:
        return json.loads(
            CORRECTION_STORE_PATH.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )
    except Exception:
        return {}


def build_correction_key(source, chunk_id):
    return f"{source}::chunk::{chunk_id}"


def save_chunk_correction(source, chunk_id, corrected_text):
    corrections = load_chunk_corrections()
    key = build_correction_key(source, chunk_id)

    corrections[key] = {
        "source": source,
        "chunk_id": chunk_id,
        "corrected_text": corrected_text,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    CORRECTION_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORRECTION_STORE_PATH.write_text(
        json.dumps(corrections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return corrections[key]


def apply_chunk_corrections(chunks):
    corrections = load_chunk_corrections()

    if not corrections:
        return chunks

    for chunk in chunks or []:
        metadata = chunk.metadata or {}
        key = build_correction_key(
            metadata.get("source", ""),
            metadata.get("chunk_id", ""),
        )
        correction = corrections.get(key)

        if not correction:
            continue

        chunk.page_content = correction.get("corrected_text", chunk.page_content)
        chunk.metadata["chunk_corrected"] = True
        chunk.metadata["chunk_correction_updated_at"] = correction.get("updated_at", "")

    return chunks
