import json
import re

from config import (
    MAX_HISTORY_MESSAGES,
    ROUTER_TEMPERATURE,
    REWRITE_TEMPERATURE,
    ANSWER_TEMPERATURE,
    REPAIR_TEMPERATURE,
    DIRECT_TEMPERATURE,
)

from prompts.router_prompts import build_task_classification_prompt
from prompts.retrieval_prompts import build_rewrite_query_prompt
from prompts.answer_prompts import build_rag_answer_prompt
from prompts.direct_prompts import build_direct_answer_prompt
from prompts.validation_prompts import build_answer_repair_prompt

from validators.task_validator import validate_task_info
from validators.answer_validator import validate_answer

from services.llm_service import get_chat_llm


def format_chat_history(chat_history, max_messages=MAX_HISTORY_MESSAGES):
    """
    将最近几轮对话格式化成 prompt 可用文本。
    """
    recent_history = chat_history[-max_messages:]
    history_text = ""

    for msg in recent_history:
        if msg["role"] == "user":
            history_text += f"用户：{msg['content']}\n"
        elif msg["role"] == "assistant":
            history_text += f"AI：{msg['content']}\n"

    return history_text.strip()


def parse_json_from_text(text):
    """
    尽量从模型输出中提取 JSON。
    """
    text = text.strip()

    text = re.sub(r"^```json", "", text)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return None


def classify_task(question, chat_history):
    """
    任务识别 Router。
    """
    history_text = format_chat_history(chat_history)

    prompt = build_task_classification_prompt(
        question=question,
        history_text=history_text,
    )

    try:
        llm = get_chat_llm(temperature=ROUTER_TEMPERATURE)
        response = llm.invoke(prompt)
        raw_result = parse_json_from_text(response.content)

        return validate_task_info(raw_result)

    except Exception:
        return validate_task_info(None)


def rewrite_question_for_retrieval(question, chat_history, task_info):
    """
    多轮追问时，把问题改写成适合检索的独立问题。
    """
    if not chat_history and task_info.get("task_type") != "summary":
        return question

    history_text = format_chat_history(chat_history)
    task_type = task_info.get("task_type", "qa")

    prompt = build_rewrite_query_prompt(
        question=question,
        history_text=history_text,
        task_type=task_type,
    )

    try:
        llm = get_chat_llm(temperature=REWRITE_TEMPERATURE)
        response = llm.invoke(prompt)
        rewritten_question = response.content.strip()

        if rewritten_question:
            return rewritten_question

        return question

    except Exception:
        return question


def build_source_summary(docs):
    """
    构造来源摘要，供答案修复使用。
    """
    lines = []

    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "未知文件")
        file_type = doc.metadata.get("file_type", "未知类型")
        location = doc.metadata.get("location", "未知位置")
        chunk_id = doc.metadata.get("chunk_id", "未知片段")

        lines.append(
            f"资料片段 {i}：{source}，{file_type}，{location}，Chunk {chunk_id}"
        )

    return "\n".join(lines)


def generate_answer_with_sources(question, docs, chat_history, task_info):
    """
    生成 RAG 答案，并进行格式校验与自动修复。
    """
    history_text = format_chat_history(chat_history)

    prompt = build_rag_answer_prompt(
        question=question,
        docs=docs,
        history_text=history_text,
        task_info=task_info,
    )

    llm = get_chat_llm(temperature=ANSWER_TEMPERATURE)
    response = llm.invoke(prompt)
    answer = response.content

    task_type = task_info.get("task_type", "qa")
    validation_result = validate_answer(answer, task_type)

    was_repaired = False

    if validation_result["is_valid"]:
        return answer, validation_result, was_repaired

    source_summary = build_source_summary(docs)

    repair_prompt = build_answer_repair_prompt(
        question=question,
        original_answer=answer,
        task_info=task_info,
        validation_result=validation_result,
        source_summary=source_summary,
    )

    repair_llm = get_chat_llm(temperature=REPAIR_TEMPERATURE)
    repair_response = repair_llm.invoke(repair_prompt)
    repaired_answer = repair_response.content

    repaired_validation_result = validate_answer(repaired_answer, task_type)
    was_repaired = True

    return repaired_answer, repaired_validation_result, was_repaired


def generate_direct_answer(question, chat_history, task_info):
    """
    无需 RAG 时直接回答。
    """
    history_text = format_chat_history(chat_history)

    prompt = build_direct_answer_prompt(
        question=question,
        history_text=history_text,
        task_info=task_info,
    )

    llm = get_chat_llm(temperature=DIRECT_TEMPERATURE)
    response = llm.invoke(prompt)

    return response.content