def build_answer_repair_prompt(
    question,
    original_answer,
    task_info,
    validation_result,
    source_summary
):
    task_type = task_info.get("task_type", "qa")
    answer_format = task_info.get("answer_format", "")
    missing_fields = validation_result.get("missing_fields", [])

    return f"""
你是一个答案格式修复助手。

下面的回答格式不符合要求，请你在不新增事实、不改变原意的前提下，
把它整理成符合任务类型的标准格式。

注意：
1. 不要编造原回答中没有的结论。
2. 不要新增资料中没有的信息。
3. 可以根据“可用依据来源”补全依据来源格式。
4. 如果原回答中没有明确答案，不要强行编造答案。
5. 只输出修复后的最终答案，不要解释你的修复过程。

【用户问题】
{question}

【任务类型】
{task_type}

【回答格式要求】
{answer_format}

【缺失字段】
{missing_fields}

【可用依据来源】
{source_summary}

【原始回答】
{original_answer}

请输出修复后的答案。
"""