REQUIRED_FIELDS_BY_TASK = {
    "qa": ["答案", "理由", "依据来源"],
    "summary": ["文档主题", "核心内容", "关键结论", "依据来源"],
    "extract_points": ["知识点整理", "重点解释", "依据来源"],
    "question_solving": ["答案", "解题思路", "详细解析", "依据来源"],
    "format_answer": ["依据来源"],
}


def _contains_heading(answer, heading):
    """
    兼容中文冒号和英文冒号。
    """
    return f"{heading}：" in answer or f"{heading}:" in answer


def validate_answer(answer, task_type):
    """
    校验最终答案格式是否符合任务类型要求。
    """
    if not isinstance(answer, str) or not answer.strip():
        return {
            "is_valid": False,
            "missing_fields": ["answer_content"],
            "message": "答案为空或不是字符串。",
        }

    required_fields = REQUIRED_FIELDS_BY_TASK.get(
        task_type,
        REQUIRED_FIELDS_BY_TASK["qa"]
    )

    missing_fields = []

    for field in required_fields:
        if not _contains_heading(answer, field):
            missing_fields.append(field)

    if "依据来源" in required_fields:
        if "资料片段" not in answer and "Chunk" not in answer:
            missing_fields.append("依据来源中的资料片段或 Chunk 信息")

    is_valid = len(missing_fields) == 0

    return {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "message": "答案格式合格。" if is_valid else "答案格式不合格，需要自动修复。",
    }