"""工具任务注册表。

数学计算不再由本地计算工具执行。
- 正常情况下，calculation 会由 AgentGraph 路由到 direct_answer_node。
- 为兼容旧版或缓存中的 AgentGraph，即使 calculation 意外进入 tool_node，
  本模块也会直接调用大模型回答，而不会调用 math_compute_tool。
"""

from __future__ import annotations

import csv
import importlib
from pathlib import Path
from typing import Any, Callable


# 计算任务不属于工具任务。日志查询仍保留工具路径。
TOOL_TASK_TYPES = {"log_query"}


def is_tool_task(task_type: str) -> bool:
    return str(task_type or "") in TOOL_TASK_TYPES


def _call_direct_llm(
    question: str,
    task_info: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """兼容旧路由：calculation 即使误入 tool_node，也直接调用大模型。"""
    from services.rag_service import generate_direct_answer

    chat_history = context.get("chat_history", [])

    attempts = (
        lambda: generate_direct_answer(
            question=question,
            chat_history=chat_history,
            task_info=task_info,
        ),
        lambda: generate_direct_answer(question, chat_history, task_info),
    )

    last_error: Exception | None = None
    for attempt in attempts:
        try:
            answer = attempt()
            return {
                "answer": str(answer),
                "error": "",
                "execution_path": "direct_llm_compat",
            }
        except TypeError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise RuntimeError("大模型直接回答调用失败。")


def _load_existing_log_runner() -> Callable[..., Any] | None:
    module_names = (
        "services.tools.log_query_tool",
        "services.tools.log_tool",
        "services.tools.runtime_log_tool",
    )
    function_names = (
        "run_log_query_tool",
        "run_log_query",
        "query_log",
    )

    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue

        for function_name in function_names:
            function = getattr(module, function_name, None)
            if callable(function):
                return function

    return None


def _call_compatible(
    function: Callable[..., Any],
    question: str,
    task_info: dict,
    context: dict,
) -> Any:
    attempts = (
        lambda: function(question=question, task_info=task_info, context=context),
        lambda: function(question=question, context=context),
        lambda: function(question, task_info, context),
        lambda: function(question, context),
        lambda: function(question),
    )

    last_error: Exception | None = None
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise RuntimeError("日志工具调用失败。")


def _read_latest_log_row() -> dict[str, str]:
    try:
        from services.log_service import LOG_FILE
    except Exception:
        return {}

    path = Path(LOG_FILE)
    if not path.exists() or path.stat().st_size == 0:
        return {}

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except Exception:
        return {}

    return rows[-1] if rows else {}


def _fallback_log_query(question: str) -> dict[str, Any]:
    row = _read_latest_log_row()
    if not row:
        return {"answer": "目前没有可读取的运行日志。", "error": ""}

    normalized_question = str(question or "").lower()
    field_groups = {
        "耗时": ("elapsed_seconds",),
        "任务类型": ("task_type",),
        "检索": ("retrieved_sources", "retrieval_question", "top_k"),
        "chunk": ("retrieved_sources", "retrieval_question", "top_k"),
        "修复": ("was_repaired", "format_valid", "missing_fields"),
        "错误": ("error",),
    }

    fields: tuple[str, ...] = tuple(row.keys())
    for token, selected_fields in field_groups.items():
        if token in normalized_question:
            fields = selected_fields
            break

    lines = []
    for field in fields:
        value = row.get(field, "")
        if value not in (None, ""):
            lines.append(f"- {field}: {value}")

    return {
        "answer": "最近一次运行记录：\n" + ("\n".join(lines) if lines else "没有对应字段。"),
        "error": "",
        "log_row": row,
    }


def run_tool_by_task_type(
    task_type: str,
    question: str,
    task_info: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task_info = task_info or {}
    context = context or {}

    # 强制兼容：旧 AgentGraph 即使把 calculation 送进 tool_node，
    # 这里也直接调用大模型，不调用任何计算工具。
    if task_type == "calculation":
        return _call_direct_llm(question, task_info, context)

    if task_type == "log_query":
        existing_runner = _load_existing_log_runner()
        if existing_runner is not None:
            result = _call_compatible(existing_runner, question, task_info, context)
            if isinstance(result, dict):
                return result
            return {"answer": str(result), "error": ""}

        return _fallback_log_query(question)

    return {
        "answer": f"暂不支持工具任务：{task_type}",
        "error": "unsupported_tool_task",
    }
