ALLOWED_TASK_TYPES = {
    "qa",
    "summary",
    "extract_points",
    "question_solving",
    "format_answer",
    "chit_chat",
    "calculation",
    "log_query",
}


DEFAULT_TASK_INFO = {
    "task_type": "qa",
    "need_rag": True,
    "answer_format": "普通问答",
    "reason": "任务识别结果无效，已回退为普通文档问答。",
}


def validate_task_info(task_info):
    """校验 Router 输出，不再保存任何计算工具参数。"""
    if not isinstance(task_info, dict):
        return DEFAULT_TASK_INFO.copy()

    task_type = task_info.get("task_type", "qa")
    if task_type not in ALLOWED_TASK_TYPES:
        return DEFAULT_TASK_INFO.copy()

    need_rag = task_info.get("need_rag", True)
    if not isinstance(need_rag, bool):
        need_rag = True

    # 计算请求直接交给大模型；日志查询仍由日志工具处理。
    if task_type in {"chit_chat", "calculation", "log_query"}:
        need_rag = False

    answer_format = task_info.get("answer_format", "普通问答")
    reason = task_info.get("reason", "")

    if not isinstance(answer_format, str) or not answer_format.strip():
        answer_format = "普通问答"

    if not isinstance(reason, str) or not reason.strip():
        reason = "Router 未提供原因。"

    return {
        "task_type": task_type,
        "need_rag": need_rag,
        "answer_format": answer_format.strip(),
        "reason": reason.strip(),
    }
