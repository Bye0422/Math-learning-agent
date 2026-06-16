import csv
import json
from pathlib import Path

from config import LOG_DIR_NAME, LOG_FILE_NAME


LOG_DIR = Path(LOG_DIR_NAME)
LOG_FILE = LOG_DIR / LOG_FILE_NAME


LOG_FIELDNAMES = [
    "timestamp",
    "session_id",
    "file_key",
    "question",
    "task_type",
    "need_rag",
    "answer_format",
    "task_reason",
    "retrieval_question",
    "top_k",
    "retrieved_sources",
    "answer_length",
    "format_valid",
    "missing_fields",
    "was_repaired",
    "elapsed_seconds",
    "error",
]


def ensure_log_file():
    """
    确保日志文件存在。
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if LOG_FILE.exists():
        return

    with open(LOG_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDNAMES)
        writer.writeheader()


def safe_json_dumps(value):
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def write_agent_log(row):
    """
    写入一轮 Agent 执行日志。
    """
    ensure_log_file()

    clean_row = {}

    for field in LOG_FIELDNAMES:
        value = row.get(field, "")

        if isinstance(value, (dict, list)):
            value = safe_json_dumps(value)

        clean_row[field] = value

    with open(LOG_FILE, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDNAMES)
        writer.writerow(clean_row)

    return clean_row


def build_retrieved_sources(results_with_scores):
    """
    整理检索命中的来源信息，便于写入日志。
    """
    sources = []

    for i, (doc, score) in enumerate(results_with_scores, start=1):
        source = doc.metadata.get("source", "未知文件")
        file_type = doc.metadata.get("file_type", "未知类型")
        location = doc.metadata.get("location", "未知位置")
        chunk_id = doc.metadata.get("chunk_id", "未知片段")
        retrieval_method = doc.metadata.get("_retrieval_method", "unknown")
        vector_distance = doc.metadata.get("_vector_distance", None)
        rule_score = doc.metadata.get("_rule_score", 0)

        sources.append({
            "rank": i,
            "source": source,
            "file_type": file_type,
            "location": location,
            "chunk_id": chunk_id,
            "retrieval_method": retrieval_method,
            "hybrid_score": round(float(score), 4),
            "vector_distance": vector_distance,
            "rule_score": rule_score,
        })

    return sources