import re
from copy import deepcopy

import config

from prompts.math_exam_prompts import (
    build_math_exam_answer_prompt,
    build_math_exam_repair_prompt,
)
from services.llm_service import get_chat_llm
from validators.math_exam_output_validator import (
    parse_and_validate_math_exam_output,
    validate_math_exam_items,
    build_answer_text_from_items,
)


def get_math_exam_temperature():
    return getattr(config, "MATH_EXAM_TEMPERATURE", 0.2)


def format_chat_history_for_math_exam(chat_history, max_messages=6):
    if not chat_history:
        return "无"

    recent_history = chat_history[-max_messages:]
    lines = []

    for item in recent_history:
        role = item.get("role", "")
        content = item.get("content", "")

        if not content:
            continue

        if role == "user":
            lines.append(f"用户：{content}")
        elif role == "assistant":
            lines.append(f"助手：{content}")
        else:
            lines.append(f"{role}：{content}")

    return "\n".join(lines) if lines else "无"


def infer_math_question_type(question, context_text=""):
    text = f"{question}\n{context_text}"

    if re.search(r"(?m)^\s*[A-D][\.、．]\s*", text):
        return "选择题"

    if re.search(r"(?m)^\s*[（(][A-D][）)]", text):
        return "选择题"

    if re.search(r"选择题|选项|选\s*[A-D]|为什么选", text):
        return "选择题"

    if re.search(r"判断题|判断正误|正确|错误|对还是错|是否正确|判断下列说法", text):
        return "判断题"

    if re.search(r"填空题|填空|空格|横线|____|___|＿+|填入", text):
        return "填空题"

    if re.search(r"简答题|简述|说明|解释|比较|论述|含义|区别|联系", text):
        return "简答题"

    if re.search(
        r"计算|证明|估计|检验|求解|求|构造|解方程|化简|因式分解|"
        r"导数|积分|极限|矩阵|向量|概率|方差|期望|函数|不等式|数列|几何",
        text,
        re.I,
    ):
        return "计算题"

    return "计算题"


def get_doc_score_text(score):
    if score is None:
        return ""

    try:
        return str(round(float(score), 4))
    except Exception:
        return str(score)


def build_math_context_and_sources(retrieved_docs_with_scores):
    context_parts = []
    source_parts = []

    for index, item in enumerate(retrieved_docs_with_scores, start=1):
        try:
            doc, score = item
        except Exception:
            continue

        metadata = deepcopy(doc.metadata or {})

        source = metadata.get("source", "")
        file_type = metadata.get("file_type", "")
        location = metadata.get("location", "")
        chunk_id = metadata.get("chunk_id", "")
        rerank_score = metadata.get("_rerank_score", "")
        rerank_reason = metadata.get("_rerank_reason", "")
        original_score = metadata.get("_original_retrieval_score", score)

        content = doc.page_content or ""

        context_parts.append(
            f"""
【资料片段 {index}】
来源文件：{source}
文件类型：{file_type}
位置：{location}
Chunk ID：{chunk_id}
最终检索分数：{get_doc_score_text(score)}
Rerank 分数：{rerank_score}
Rerank 理由：{rerank_reason}
原始检索分数：{get_doc_score_text(original_score)}

内容：
{content}
""".strip()
        )

        source_parts.append(
            f"资料片段 {index}：来源文件={source}；位置={location}；Chunk ID={chunk_id}"
        )

    context_text = "\n\n".join(context_parts) if context_parts else "无可用资料片段"
    sources_text = "\n".join(source_parts) if source_parts else "无"

    return context_text, sources_text


def call_llm(prompt, temperature=None):
    if temperature is None:
        temperature = get_math_exam_temperature()

    try:
        llm = get_chat_llm(temperature=temperature)
    except TypeError:
        llm = get_chat_llm()

    response = llm.invoke(prompt)

    if hasattr(response, "content"):
        return response.content

    return str(response)


def repair_math_exam_output(
    raw_output,
    question,
    task_type,
    question_type,
    validation_errors,
):
    repair_prompt = build_math_exam_repair_prompt(
        raw_output=raw_output,
        question=question,
        task_type=task_type,
        question_type=question_type,
        validation_errors=validation_errors,
    )

    repaired_output = call_llm(
        repair_prompt,
        temperature=0.1,
    )

    return repaired_output


def generate_math_exam_answer(
    question,
    task_info,
    retrieved_docs_with_scores,
    chat_history=None,
):
    if chat_history is None:
        chat_history = []

    if task_info is None:
        task_info = {}

    task_type = task_info.get("task_type", "question_solving")

    context_text, sources_text = build_math_context_and_sources(
        retrieved_docs_with_scores
    )

    question_type = infer_math_question_type(
        question=question,
        context_text=context_text,
    )

    chat_history_text = format_chat_history_for_math_exam(chat_history)

    prompt = build_math_exam_answer_prompt(
        question=question,
        task_type=task_type,
        question_type=question_type,
        context_text=context_text,
        sources_text=sources_text,
        chat_history_text=chat_history_text,
    )

    raw_output = call_llm(
        prompt,
        temperature=get_math_exam_temperature(),
    )

    was_repaired = False

    try:
        validation_result = parse_and_validate_math_exam_output(raw_output)
    except Exception as e:
        validation_result = {
            "valid": False,
            "errors": [str(e)],
            "items": [],
        }

    if not validation_result.get("valid", False):
        try:
            repaired_output = repair_math_exam_output(
                raw_output=raw_output,
                question=question,
                task_type=task_type,
                question_type=question_type,
                validation_errors=validation_result.get("errors", []),
            )

            repaired_validation = parse_and_validate_math_exam_output(
                repaired_output
            )

            validation_result = repaired_validation
            raw_output = repaired_output
            was_repaired = True

        except Exception as e:
            validation_result["repair_error"] = str(e)

    items = validation_result.get("items", [])

    if not items:
        items = [
            {
                "analysis": "根据当前资料无法完全确定, 缺少可用于生成解析的有效题干、选项、答案或计算条件.",
                "difficulty": 2,
                "type": question_type if question_type in ["选择题", "判断题", "简答题", "填空题", "计算题"] else "计算题",
                "tags": ["数学"],
            }
        ]

        validation_result = validate_math_exam_items(items)

    answer_text = build_answer_text_from_items(items)

    return {
        "answer": answer_text,
        "items": items,
        "validation_result": validation_result,
        "was_repaired": was_repaired,
        "question_type": question_type,
    }