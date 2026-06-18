import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


# =========================
# 项目路径处理
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from config import (  # noqa: E402
    ENABLE_RERANK,
    ENABLE_SQLITE_MEMORY,
    ENABLE_PDF_PARSE_QUALITY_CHECK,
)

from services.document_loader import read_multiple_files_to_documents  # noqa: E402
from services.vector_service import split_documents, create_vector_db  # noqa: E402
from services.agent_graph import run_agent_graph  # noqa: E402
from services.log_service import ensure_log_file, write_agent_log, build_retrieved_sources  # noqa: E402
from evals.build_eval_report import write_eval_report  # noqa: E402

try:
    from services.memory_service import init_memory_db, save_qa_turn
except Exception:
    init_memory_db = None
    save_qa_turn = None


# =========================
# 路径配置
# =========================

EVAL_DIR = PROJECT_ROOT / "evals"
SOURCE_DOCS_DIR = EVAL_DIR / "source_docs"
CASES_PATH = EVAL_DIR / "eval_cases_v2.json"
OUTPUT_DIR = EVAL_DIR / "eval_outputs"

RESULTS_CSV_PATH = OUTPUT_DIR / "eval_results_v2.csv"
SUMMARY_JSON_PATH = OUTPUT_DIR / "eval_summary_v2.json"
TREND_JSON_PATH = OUTPUT_DIR / "eval_trend_v2.json"


SUPPORTED_FILE_SUFFIXES = {
    ".pdf",
    ".docx",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


# =========================
# 模拟 Streamlit uploaded_file
# =========================

class LocalUploadedFile:
    """
    模拟 Streamlit uploaded_file，让现有 document_loader 可以复用。
    """

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.name = self.file_path.name
        self.size = self.file_path.stat().st_size
        self._bytes = self.file_path.read_bytes()
        self._pos = 0

    def read(self, size=-1):
        if size is None or size < 0:
            data = self._bytes[self._pos:]
            self._pos = len(self._bytes)
            return data

        data = self._bytes[self._pos:self._pos + size]
        self._pos += size
        return data

    def seek(self, pos):
        self._pos = pos

    def tell(self):
        return self._pos


# =========================
# 工具函数
# =========================

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_eval_cases():
    if not CASES_PATH.exists():
        raise FileNotFoundError(f"没有找到评估集文件：{CASES_PATH}")

    return json.loads(
        CASES_PATH.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )


def collect_source_files():
    if not SOURCE_DOCS_DIR.exists():
        SOURCE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        return []

    files = []

    for path in SOURCE_DOCS_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_FILE_SUFFIXES:
            files.append(path)

    return files


def load_documents_from_source_docs():
    """
    从 evals/source_docs 读取评估文档。
    """
    source_files = collect_source_files()

    if not source_files:
        return {
            "documents": [],
            "chunks": [],
            "vector_db": None,
            "load_errors": [],
            "source_files": [],
            "doc_stats": {},
        }

    uploaded_files = [
        LocalUploadedFile(path)
        for path in source_files
    ]

    documents, load_errors = read_multiple_files_to_documents(uploaded_files)

    if not documents:
        return {
            "documents": [],
            "chunks": [],
            "vector_db": None,
            "load_errors": load_errors,
            "source_files": [str(p) for p in source_files],
            "doc_stats": build_doc_stats(documents),
        }

    chunks = split_documents(documents)
    vector_db = create_vector_db(chunks)

    return {
        "documents": documents,
        "chunks": chunks,
        "vector_db": vector_db,
        "load_errors": load_errors,
        "source_files": [str(p) for p in source_files],
        "doc_stats": build_doc_stats(documents),
    }


def build_doc_stats(documents):
    """
    统计文档解析情况，包括 MinerU 缓存和 PDF 质量评分。
    """
    stats = {
        "document_count": len(documents),
        "pdf_mineru_count": 0,
        "pdf_mineru_cache_count": 0,
        "pdf_pypdf_count": 0,
        "pdf_quality_scores": [],
        "pdf_quality_levels": [],
        "pdf_quality_issues": [],
        "sources": [],
    }

    for doc in documents:
        metadata = doc.metadata or {}

        source = metadata.get("source", "")
        file_type = metadata.get("file_type", "")

        if source:
            stats["sources"].append(source)

        if file_type == "pdf_mineru":
            stats["pdf_mineru_count"] += 1

        if file_type == "pdf_mineru_cache":
            stats["pdf_mineru_cache_count"] += 1

        if file_type == "pdf_pypdf":
            stats["pdf_pypdf_count"] += 1

        if metadata.get("pdf_quality_score", "") != "":
            stats["pdf_quality_scores"].append(metadata.get("pdf_quality_score", ""))
            stats["pdf_quality_levels"].append(metadata.get("pdf_quality_level", ""))
            stats["pdf_quality_issues"].append(metadata.get("pdf_quality_issues", ""))

    stats["sources"] = list(sorted(set(stats["sources"])))

    return stats


def contains_all_fields(answer, fields):
    """
    检查答案是否包含必需字段。
    """
    if not fields:
        return True, []

    missing = []

    for field in fields:
        if field not in answer:
            missing.append(field)

    return len(missing) == 0, missing


def keyword_hit_score(text, keywords):
    """
    关键词命中比例。
    """
    if not keywords:
        return 1.0, []

    text = text or ""
    hit_keywords = []

    for keyword in keywords:
        if keyword and keyword in text:
            hit_keywords.append(keyword)

    return round(len(hit_keywords) / len(keywords), 4), hit_keywords


def build_retrieved_text(retrieved_docs_with_scores):
    parts = []

    for doc, score in retrieved_docs_with_scores:
        metadata = doc.metadata or {}
        parts.append(
            "\n".join(
                [
                    f"source={metadata.get('source', '')}",
                    f"file_type={metadata.get('file_type', '')}",
                    f"location={metadata.get('location', '')}",
                    f"score={score}",
                    doc.page_content or "",
                ]
            )
        )

    return "\n\n".join(parts)


def safe_get_task_info(graph_result):
    task_info = graph_result.get("task_info", {})

    if not isinstance(task_info, dict):
        return {}

    return task_info


def evaluate_single_case(case, shared_context, chat_history):
    """
    执行单条 eval case。
    """
    case_id = case.get("case_id", "")
    question = case.get("question", "")
    requires_docs = case.get("requires_docs", False)

    expected_task_type = case.get("expected_task_type", "")
    expected_route = case.get("expected_route", "")
    expected_need_rag = case.get("expected_need_rag", None)
    expected_answer_keywords = case.get("expected_answer_keywords", [])
    expected_source_keywords = case.get("expected_source_keywords", [])
    must_have_fields = case.get("must_have_fields", [])

    vector_db = shared_context.get("vector_db")
    chunks = shared_context.get("chunks", [])

    if requires_docs and vector_db is None:
        return {
            "case_id": case_id,
            "case_type": case.get("case_type", ""),
            "question": question,
            "status": "skipped",
            "skip_reason": "requires_docs=True，但 evals/source_docs 没有成功构建向量库。",
            "task_type": "",
            "route": "",
            "need_rag": "",
            "task_type_correct": "",
            "route_correct": "",
            "need_rag_correct": "",
            "answer_keyword_score": "",
            "answer_hit_keywords": "",
            "source_keyword_score": "",
            "source_hit_keywords": "",
            "must_have_fields_valid": "",
            "missing_fields": "",
            "retrieval_question": "",
            "retrieved_count": "",
            "candidate_count": "",
            "rerank_used": "",
            "rerank_score_avg": "",
            "format_valid": "",
            "was_repaired": "",
            "elapsed_seconds": "",
            "error": "",
            "answer": "",
        }

    start_time = time.time()

    graph_result = run_agent_graph(
        question=question,
        chat_history=chat_history,
        vector_db=vector_db,
        chunks=chunks,
    )

    elapsed_seconds = round(time.time() - start_time, 4)

    task_info = safe_get_task_info(graph_result)
    answer = graph_result.get("answer", "")
    route = graph_result.get("route", "")
    retrieval_question = graph_result.get("retrieval_question", "")
    retrieved_docs_with_scores = graph_result.get("retrieved_docs_with_scores", [])
    candidate_docs_with_scores = graph_result.get("candidate_docs_with_scores", [])
    validation_result = graph_result.get("validation_result", {})
    was_repaired = graph_result.get("was_repaired", False)
    graph_error = graph_result.get("error", "")

    task_type = task_info.get("task_type", "")
    need_rag = task_info.get("need_rag", "")

    task_type_correct = int(task_type == expected_task_type) if expected_task_type else ""
    route_correct = int(route == expected_route) if expected_route else ""

    if expected_need_rag is None:
        need_rag_correct = ""
    else:
        need_rag_correct = int(need_rag == expected_need_rag)

    answer_keyword_score, answer_hit_keywords = keyword_hit_score(
        answer,
        expected_answer_keywords,
    )

    retrieved_text = build_retrieved_text(retrieved_docs_with_scores)

    source_keyword_score, source_hit_keywords = keyword_hit_score(
        retrieved_text,
        expected_source_keywords,
    )

    must_have_fields_valid, missing_fields = contains_all_fields(
        answer,
        must_have_fields,
    )

    rerank_scores = []

    for doc, _ in retrieved_docs_with_scores:
        metadata = doc.metadata or {}
        score = metadata.get("_rerank_score", "")

        try:
            if score != "":
                rerank_scores.append(float(score))
        except Exception:
            pass

    rerank_score_avg = (
        round(sum(rerank_scores) / len(rerank_scores), 4)
        if rerank_scores
        else ""
    )

    format_valid = ""

    if isinstance(validation_result, dict):
        format_valid = validation_result.get("valid", "")

    # 更新 eval 脚本内部的 chat_history，让多轮问题可以继续
    chat_history.append({
        "role": "user",
        "content": question,
    })

    chat_history.append({
        "role": "assistant",
        "content": answer,
    })

    return {
        "case_id": case_id,
        "case_type": case.get("case_type", ""),
        "question": question,
        "status": "ok",
        "skip_reason": "",
        "task_type": task_type,
        "route": route,
        "need_rag": need_rag,
        "task_type_correct": task_type_correct,
        "route_correct": route_correct,
        "need_rag_correct": need_rag_correct,
        "answer_keyword_score": answer_keyword_score,
        "answer_hit_keywords": "；".join(answer_hit_keywords),
        "source_keyword_score": source_keyword_score,
        "source_hit_keywords": "；".join(source_hit_keywords),
        "must_have_fields_valid": int(must_have_fields_valid),
        "missing_fields": "；".join(missing_fields),
        "retrieval_question": retrieval_question,
        "retrieved_count": len(retrieved_docs_with_scores),
        "candidate_count": len(candidate_docs_with_scores),
        "rerank_used": graph_result.get("rerank_used", ""),
        "rerank_score_avg": rerank_score_avg,
        "format_valid": format_valid,
        "was_repaired": int(bool(was_repaired)),
        "elapsed_seconds": graph_result.get("elapsed_seconds", elapsed_seconds),
        "error": graph_error,
        "answer": answer,
    }


def average_numeric(rows, field):
    values = []

    for row in rows:
        value = row.get(field, "")

        if value == "":
            continue

        try:
            values.append(float(value))
        except Exception:
            pass

    if not values:
        return ""

    return round(sum(values) / len(values), 4)


def sum_numeric(rows, field):
    total = 0

    for row in rows:
        value = row.get(field, "")

        try:
            total += int(value)
        except Exception:
            pass

    return total


def build_summary(results, doc_context, started_at, finished_at):
    ok_rows = [
        row for row in results
        if row.get("status") == "ok"
    ]

    skipped_rows = [
        row for row in results
        if row.get("status") == "skipped"
    ]

    total_cases = len(results)
    ok_cases = len(ok_rows)
    skipped_cases = len(skipped_rows)

    summary = {
        "started_at": started_at,
        "finished_at": finished_at,
        "total_cases": total_cases,
        "ok_cases": ok_cases,
        "skipped_cases": skipped_cases,
        "enable_rerank": ENABLE_RERANK,
        "enable_sqlite_memory": ENABLE_SQLITE_MEMORY,
        "enable_pdf_parse_quality_check": ENABLE_PDF_PARSE_QUALITY_CHECK,
        "source_docs": doc_context.get("source_files", []),
        "load_errors": doc_context.get("load_errors", []),
        "doc_stats": doc_context.get("doc_stats", {}),
        "metrics": {
            "task_type_accuracy": average_numeric(ok_rows, "task_type_correct"),
            "route_accuracy": average_numeric(ok_rows, "route_correct"),
            "need_rag_accuracy": average_numeric(ok_rows, "need_rag_correct"),
            "answer_keyword_score_avg": average_numeric(ok_rows, "answer_keyword_score"),
            "source_keyword_score_avg": average_numeric(ok_rows, "source_keyword_score"),
            "must_have_fields_valid_rate": average_numeric(ok_rows, "must_have_fields_valid"),
            "format_valid_rate": average_numeric(ok_rows, "format_valid"),
            "repair_trigger_rate": average_numeric(ok_rows, "was_repaired"),
            "rerank_usage_rate": average_numeric(ok_rows, "rerank_used"),
            "rerank_score_avg": average_numeric(ok_rows, "rerank_score_avg"),
            "retrieved_count_avg": average_numeric(ok_rows, "retrieved_count"),
            "candidate_count_avg": average_numeric(ok_rows, "candidate_count"),
            "elapsed_seconds_avg": average_numeric(ok_rows, "elapsed_seconds"),
            "error_count": sum(1 for row in ok_rows if row.get("error")),
        },
    }

    return summary


def _metric_value(metrics, *names):
    for name in names:
        value = metrics.get(name, "")

        if value == "":
            continue

        try:
            return round(float(value), 4)
        except Exception:
            continue

    return ""


def _int_metric(metrics, name):
    value = metrics.get(name, 0)

    try:
        return int(value or 0)
    except Exception:
        return 0


def build_trend_entry(summary):
    metrics = summary.get("metrics", {})

    return {
        "started_at": summary.get("started_at", ""),
        "finished_at": summary.get("finished_at", ""),
        "total_cases": summary.get("total_cases", 0),
        "ok_cases": summary.get("ok_cases", 0),
        "skipped_cases": summary.get("skipped_cases", 0),
        "hit_rate": _metric_value(
            metrics,
            "source_keyword_score_avg",
            "answer_keyword_score_avg",
        ),
        "format_valid_rate": _metric_value(metrics, "format_valid_rate"),
        "elapsed_seconds_avg": _metric_value(metrics, "elapsed_seconds_avg"),
        "rerank_usage_rate": _metric_value(metrics, "rerank_usage_rate"),
        "error_count": _int_metric(metrics, "error_count"),
    }


def build_trend_report(history):
    if not history:
        return {
            "latest": {},
            "previous": {},
            "delta": {},
            "history": [],
        }

    latest = history[-1]
    previous = history[-2] if len(history) >= 2 else {}

    delta = {}

    for field in [
        "hit_rate",
        "format_valid_rate",
        "elapsed_seconds_avg",
        "rerank_usage_rate",
        "error_count",
    ]:
        latest_value = latest.get(field, "")
        previous_value = previous.get(field, "")

        if latest_value == "" or previous_value == "":
            delta[field] = ""
            continue

        try:
            delta[field] = round(float(latest_value) - float(previous_value), 4)
        except Exception:
            delta[field] = ""

    return {
        "latest": latest,
        "previous": previous,
        "delta": delta,
        "history": history,
    }


def update_trend_report(summary):
    history = []

    if TREND_JSON_PATH.exists():
        try:
            data = json.loads(TREND_JSON_PATH.read_text(encoding="utf-8"))

            if isinstance(data, dict) and isinstance(data.get("history"), list):
                history = data["history"]
            elif isinstance(data, list):
                history = data
        except Exception:
            history = []

    history.append(build_trend_entry(summary))
    report = build_trend_report(history)

    TREND_JSON_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return report


def write_results_csv(results):
    if not results:
        return

    fieldnames = list(results[0].keys())

    with RESULTS_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(results)


def write_summary_json(summary):
    SUMMARY_JSON_PATH.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def ensure_fake_log_for_log_query():
    """
    给 log_query 工具提供一条基础日志，避免评估时日志为空。
    """
    ensure_log_file()

    fake_log_row = {
        "timestamp": now_text(),
        "session_id": "eval_session",
        "file_key": "eval",
        "question": "eval fake question",
        "task_type": "qa",
        "need_rag": "True",
        "answer_format": "普通问答",
        "task_reason": "Eval 初始化日志。",
        "retrieval_question": "eval fake retrieval question",
        "top_k": "3",
        "retrieved_sources": [],
        "answer_length": 0,
        "format_valid": "",
        "missing_fields": [],
        "was_repaired": 0,
        "elapsed_seconds": 0,
        "error": "",
    }

    try:
        write_agent_log(fake_log_row)
    except Exception:
        pass


def run_eval():
    ensure_output_dir()
    ensure_fake_log_for_log_query()

    if ENABLE_SQLITE_MEMORY and init_memory_db is not None:
        try:
            init_memory_db()
        except Exception:
            pass

    started_at = now_text()

    print("========== Eval V2 开始 ==========")
    print(f"项目目录：{PROJECT_ROOT}")
    print(f"评估集：{CASES_PATH}")
    print(f"文档目录：{SOURCE_DOCS_DIR}")
    print("正在加载评估文档...")

    doc_context = load_documents_from_source_docs()

    print(f"原始 Document 数：{len(doc_context.get('documents', []))}")
    print(f"Chunk 数：{len(doc_context.get('chunks', []))}")
    print(f"向量库是否建立：{doc_context.get('vector_db') is not None}")

    if doc_context.get("load_errors"):
        print("文档读取 warning：")
        for error in doc_context["load_errors"]:
            print(f"- {error}")

    cases = load_eval_cases()

    results = []
    chat_history = []

    for index, case in enumerate(cases, start=1):
        print(f"\n[{index}/{len(cases)}] Running {case.get('case_id')}：{case.get('question')}")

        try:
            result = evaluate_single_case(
                case=case,
                shared_context=doc_context,
                chat_history=chat_history,
            )

        except Exception as e:
            result = {
                "case_id": case.get("case_id", ""),
                "case_type": case.get("case_type", ""),
                "question": case.get("question", ""),
                "status": "error",
                "skip_reason": "",
                "task_type": "",
                "route": "",
                "need_rag": "",
                "task_type_correct": "",
                "route_correct": "",
                "need_rag_correct": "",
                "answer_keyword_score": "",
                "answer_hit_keywords": "",
                "source_keyword_score": "",
                "source_hit_keywords": "",
                "must_have_fields_valid": "",
                "missing_fields": "",
                "retrieval_question": "",
                "retrieved_count": "",
                "candidate_count": "",
                "rerank_used": "",
                "rerank_score_avg": "",
                "format_valid": "",
                "was_repaired": "",
                "elapsed_seconds": "",
                "error": str(e),
                "answer": "",
            }

        results.append(result)

        print(
            f"status={result.get('status')} | "
            f"task={result.get('task_type')} | "
            f"route={result.get('route')} | "
            f"answer_score={result.get('answer_keyword_score')} | "
            f"source_score={result.get('source_keyword_score')} | "
            f"error={result.get('error')}"
        )

        if ENABLE_SQLITE_MEMORY and save_qa_turn is not None and result.get("status") == "ok":
            try:
                save_qa_turn(
                    session_id="eval_session",
                    question=result.get("question", ""),
                    answer=result.get("answer", ""),
                    file_key="eval_source_docs",
                    file_names=doc_context.get("source_files", []),
                    task_info={
                        "task_type": result.get("task_type", ""),
                        "need_rag": result.get("need_rag", ""),
                        "answer_format": "",
                    },
                    route=result.get("route", ""),
                    retrieval_question=result.get("retrieval_question", ""),
                    top_k=result.get("retrieved_count", ""),
                    candidate_top_n=result.get("candidate_count", ""),
                    rerank_used=result.get("rerank_used", False),
                    retrieved_sources=[],
                    validation_result={
                        "valid": result.get("format_valid", ""),
                    },
                    was_repaired=bool(result.get("was_repaired", 0)),
                    elapsed_seconds=result.get("elapsed_seconds", 0),
                    error=result.get("error", ""),
                )
            except Exception:
                pass

    finished_at = now_text()

    summary = build_summary(
        results=results,
        doc_context=doc_context,
        started_at=started_at,
        finished_at=finished_at,
    )

    write_results_csv(results)
    write_summary_json(summary)
    trend_report = update_trend_report(summary)
    report_path = write_eval_report()

    print("\n========== Eval V2 完成 ==========")
    print(f"结果 CSV：{RESULTS_CSV_PATH}")
    print(f"汇总 JSON：{SUMMARY_JSON_PATH}")
    print(f"报告 HTML：{report_path}")
    print("\n核心指标：")
    for key, value in summary["metrics"].items():
        print(f"- {key}: {value}")

    print("\nTrend delta:")
    for key, value in trend_report["delta"].items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    run_eval()
