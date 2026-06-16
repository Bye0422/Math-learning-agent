import json
import re
from copy import deepcopy

from langchain_core.documents import Document

from config import (
    RERANK_MAX_CHARS_PER_CHUNK,
    RERANK_TEMPERATURE,
    RERANK_FALLBACK_TO_ORIGINAL,
)

from prompts.rerank_prompts import build_rerank_prompt
from services.llm_service import get_chat_llm


def truncate_text(text, max_chars):
    """
    截断过长 chunk，避免 rerank prompt 太长。
    """
    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n\n……内容过长，已截断……"


def build_candidate_text(index, doc, original_score):
    """
    构造单个候选片段文本。
    """
    metadata = doc.metadata or {}

    source = metadata.get("source", "")
    file_type = metadata.get("file_type", "")
    location = metadata.get("location", "")
    chunk_id = metadata.get("chunk_id", "")

    content = truncate_text(
        doc.page_content,
        RERANK_MAX_CHARS_PER_CHUNK,
    )

    return f"""
【片段 {index}】
来源文件：{source}
文件类型：{file_type}
位置：{location}
Chunk ID：{chunk_id}
原始检索分数：{original_score}

内容：
{content}
""".strip()


def build_candidates_text(docs_with_scores):
    """
    将候选 chunk 列表转成 rerank prompt 需要的文本。
    """
    parts = []

    for index, item in enumerate(docs_with_scores, start=1):
        doc, score = item
        parts.append(
            build_candidate_text(
                index=index,
                doc=doc,
                original_score=score,
            )
        )

    return "\n\n".join(parts)


def extract_json_array(text):
    """
    从模型输出中提取 JSON 数组。
    """
    if not text:
        raise ValueError("Rerank 模型输出为空。")

    text = text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    match = re.search(r"\[.*\]", text, re.S)

    if not match:
        raise ValueError(f"没有找到 JSON 数组：{text[:500]}")

    data = json.loads(match.group(0))

    if not isinstance(data, list):
        raise ValueError("Rerank 输出不是 JSON 数组。")

    return data


def normalize_rerank_score(score):
    """
    规范化分数到 0-5。
    """
    try:
        score = float(score)
    except Exception:
        score = 0.0

    if score < 0:
        score = 0.0

    if score > 5:
        score = 5.0

    return score


def call_llm_for_rerank(question, docs_with_scores):
    """
    调用大模型进行 Rerank。
    """
    candidates_text = build_candidates_text(docs_with_scores)

    prompt = build_rerank_prompt(
        question=question,
        candidates_text=candidates_text,
    )

    try:
        llm = get_chat_llm(temperature=RERANK_TEMPERATURE)
    except TypeError:
        llm = get_chat_llm()

    response = llm.invoke(prompt)

    if hasattr(response, "content"):
        return response.content

    return str(response)


def build_fallback_results(docs_with_scores, error_message):
    """
    Rerank 失败时，保留原始 Hybrid Retrieval 排序。
    """
    fallback_results = []

    for doc, original_score in docs_with_scores:
        new_doc = Document(
            page_content=doc.page_content,
            metadata=deepcopy(doc.metadata or {}),
        )

        new_doc.metadata["_rerank_used"] = False
        new_doc.metadata["_rerank_score"] = ""
        new_doc.metadata["_rerank_reason"] = ""
        new_doc.metadata["_rerank_error"] = error_message
        new_doc.metadata["_original_retrieval_score"] = original_score

        fallback_results.append((new_doc, original_score))

    return fallback_results


def rerank_docs_with_llm(question, docs_with_scores, final_top_k):
    """
    LLM Rerank 主入口。

    输入：
    - question：用户问题或改写后的检索问题
    - docs_with_scores：Hybrid Retrieval 返回的候选片段
    - final_top_k：最终保留多少个片段

    输出：
    - [(Document, final_score), ...]
    """
    if not docs_with_scores:
        return []

    if len(docs_with_scores) == 1:
        return docs_with_scores

    try:
        llm_output = call_llm_for_rerank(
            question=question,
            docs_with_scores=docs_with_scores,
        )

        rerank_items = extract_json_array(llm_output)

        score_map = {}

        for item in rerank_items:
            index = item.get("index")
            score = item.get("score", 0)
            reason = item.get("reason", "")

            try:
                index = int(index)
            except Exception:
                continue

            if index < 1 or index > len(docs_with_scores):
                continue

            score_map[index] = {
                "score": normalize_rerank_score(score),
                "reason": str(reason),
            }

        reranked_results = []

        for index, item in enumerate(docs_with_scores, start=1):
            doc, original_score = item

            rerank_info = score_map.get(
                index,
                {
                    "score": 0.0,
                    "reason": "模型未返回该片段评分。",
                },
            )

            rerank_score = rerank_info["score"]
            rerank_reason = rerank_info["reason"]

            new_doc = Document(
                page_content=doc.page_content,
                metadata=deepcopy(doc.metadata or {}),
            )

            new_doc.metadata["_rerank_used"] = True
            new_doc.metadata["_rerank_score"] = rerank_score
            new_doc.metadata["_rerank_reason"] = rerank_reason
            new_doc.metadata["_original_retrieval_score"] = original_score

            reranked_results.append(
                (
                    new_doc,
                    rerank_score,
                )
            )

        reranked_results = sorted(
            reranked_results,
            key=lambda x: x[1],
            reverse=True,
        )

        return reranked_results[:final_top_k]

    except Exception as e:
        error_message = str(e)

        if RERANK_FALLBACK_TO_ORIGINAL:
            return build_fallback_results(
                docs_with_scores=docs_with_scores[:final_top_k],
                error_message=error_message,
            )

        raise