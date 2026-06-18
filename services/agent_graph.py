import time
from typing import Any, Dict, Literal

import config
from services.math_exam_service import generate_math_exam_answer

from langgraph.graph import StateGraph, START, END

from services.rerank_service import rerank_docs_with_llm

from config import (
    DEFAULT_TOP_K,
    SUMMARY_TOP_K,
    EXTRACT_POINTS_TOP_K,
    ENABLE_RERANK,
    RERANK_CANDIDATE_TOP_N,
)

from services.agent_state import AgentState
from services.rag_service import (
    classify_task,
    rewrite_question_for_retrieval,
    generate_direct_answer,
    generate_answer_with_sources,
)
from services.retrieval_service import hybrid_retrieve
from services.tools.tool_registry import (
    is_tool_task,
    run_tool_by_task_type,
)


def get_top_k_by_task_type(task_type: str) -> int:
    """
    根据任务类型选择检索数量。
    """
    if task_type == "summary":
        return SUMMARY_TOP_K

    if task_type == "extract_points":
        return EXTRACT_POINTS_TOP_K

    return DEFAULT_TOP_K


def router_node(state: AgentState) -> Dict[str, Any]:
    """
    Router 节点：
    根据用户问题判断任务类型。
    """
    question = state.get("question", "")
    chat_history = state.get("chat_history", [])

    try:
        task_info = classify_task(
            question=question,
            chat_history=chat_history,
        )

        task_type = task_info.get("task_type", "qa")

        if is_tool_task(task_type):
            route = "tool"
        elif not task_info.get("need_rag", True):
            route = "direct"
        else:
            route = "rag"

        return {
            "task_info": task_info,
            "route": route,
            "error": "",
        }

    except TypeError:
        # 兼容旧版本 classify_task(question, chat_history)
        try:
            task_info = classify_task(question, chat_history)
            task_type = task_info.get("task_type", "qa")

            if is_tool_task(task_type):
                route = "tool"
            elif not task_info.get("need_rag", True):
                route = "direct"
            else:
                route = "rag"

            return {
                "task_info": task_info,
                "route": route,
                "error": "",
            }

        except Exception as e:
            return {
                "task_info": {
                    "task_type": "qa",
                    "need_rag": True,
                    "answer_format": "普通问答",
                    "reason": "Router 执行失败，已回退为普通文档问答。",
                },
                "route": "rag",
                "error": f"Router 执行失败：{e}",
            }

    except Exception as e:
        return {
            "task_info": {
                "task_type": "qa",
                "need_rag": True,
                "answer_format": "普通问答",
                "reason": "Router 执行失败，已回退为普通文档问答。",
            },
            "route": "rag",
            "error": f"Router 执行失败：{e}",
        }


def route_after_router(state: AgentState) -> Literal["tool_node", "direct_answer_node", "rag_retrieval_node"]:
    """
    条件边：
    根据 router_node 的结果决定下一步走哪里。
    """
    route = state.get("route", "rag")

    if route == "tool":
        return "tool_node"

    if route == "direct":
        return "direct_answer_node"

    return "rag_retrieval_node"


def tool_node(state: AgentState) -> Dict[str, Any]:
    """
    工具调用节点：
    calculation、log_query 等工具任务都会走这里。
    """
    question = state.get("question", "")
    task_info = state.get("task_info", {})
    task_type = task_info.get("task_type", "")

    try:
        tool_result = run_tool_by_task_type(
            task_type=task_type,
            question=question,
            task_info=task_info,
            context={
                "chat_history": state.get("chat_history", []),
            },
        )

        answer = tool_result.get("answer", "")

        return {
            "tool_result": tool_result,
            "answer": answer,
            "retrieval_question": "",
            "retrieved_docs_with_scores": [],
            "validation_result": {},
            "was_repaired": False,
            "error": tool_result.get("error", ""),
        }

    except Exception as e:
        return {
            "tool_result": {},
            "answer": f"工具调用失败：{e}",
            "retrieval_question": "",
            "retrieved_docs_with_scores": [],
            "validation_result": {},
            "was_repaired": False,
            "error": str(e),
        }


def direct_answer_node(state: AgentState) -> Dict[str, Any]:
    """
    直接回答节点：
    用于 chit_chat 或其他不需要 RAG 的问题。
    """
    question = state.get("question", "")
    chat_history = state.get("chat_history", [])
    task_info = state.get("task_info", {})

    try:
        try:
            answer = generate_direct_answer(
                question=question,
                chat_history=chat_history,
                task_info=task_info,
            )
        except TypeError:
            # 兼容旧版本 generate_direct_answer(question, chat_history, task_info)
            answer = generate_direct_answer(question, chat_history, task_info)

        return {
            "answer": answer,
            "retrieval_question": "",
            "retrieved_docs_with_scores": [],
            "validation_result": {},
            "was_repaired": False,
            "error": "",
        }

    except Exception as e:
        return {
            "answer": f"直接回答失败：{e}",
            "retrieval_question": "",
            "retrieved_docs_with_scores": [],
            "validation_result": {},
            "was_repaired": False,
            "error": str(e),
        }


def rag_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    RAG 检索节点：
    先改写检索问题，再调用 Hybrid Retrieval。
    如果开启 Rerank，则先多召回候选 chunk，再进行 LLM Rerank。
    """
    question = state.get("question", "")
    chat_history = state.get("chat_history", [])
    task_info = state.get("task_info", {})
    vector_db = state.get("vector_db")
    chunks = state.get("chunks", [])

    if vector_db is None:
        return {
            "answer": "请先上传文档并建立向量库，然后再提问。",
            "retrieval_question": "",
            "candidate_docs_with_scores": [],
            "retrieved_docs_with_scores": [],
            "top_k": 0,
            "candidate_top_n": 0,
            "rerank_used": False,
            "error": "vector_db is None",
        }

    if not chunks:
        return {
            "answer": "当前没有可检索的文档 chunk，请先完成文档读取和切分。",
            "retrieval_question": "",
            "candidate_docs_with_scores": [],
            "retrieved_docs_with_scores": [],
            "top_k": 0,
            "candidate_top_n": 0,
            "rerank_used": False,
            "error": "chunks is empty",
        }

    try:
        # 这里是本次修复的重点：
        # 你的 rewrite_question_for_retrieval 需要 task_info，所以这里必须传进去。
        try:
            retrieval_question = rewrite_question_for_retrieval(
                question=question,
                chat_history=chat_history,
                task_info=task_info,
            )
        except TypeError:
            try:
                retrieval_question = rewrite_question_for_retrieval(
                    question,
                    chat_history,
                    task_info,
                )
            except TypeError:
                retrieval_question = rewrite_question_for_retrieval(
                    question,
                    chat_history,
                )

        task_type = task_info.get("task_type", "qa")
        final_top_k = get_top_k_by_task_type(task_type)

        if ENABLE_RERANK:
            candidate_top_n = max(
                RERANK_CANDIDATE_TOP_N,
                final_top_k,
            )
        else:
            candidate_top_n = final_top_k

        candidate_docs_with_scores = hybrid_retrieve(
            vector_db=vector_db,
            chunks=chunks,
            query=retrieval_question,
            top_k=candidate_top_n,
            original_query=question,
        )

        if ENABLE_RERANK and candidate_docs_with_scores:
            retrieved_docs_with_scores = rerank_docs_with_llm(
                question=retrieval_question,
                docs_with_scores=candidate_docs_with_scores,
                final_top_k=final_top_k,
            )
            rerank_used = True
        else:
            retrieved_docs_with_scores = candidate_docs_with_scores[:final_top_k]
            rerank_used = False

        return {
            "retrieval_question": retrieval_question,
            "candidate_docs_with_scores": candidate_docs_with_scores,
            "retrieved_docs_with_scores": retrieved_docs_with_scores,
            "top_k": final_top_k,
            "candidate_top_n": candidate_top_n,
            "rerank_used": rerank_used,
            "error": "",
        }

    except Exception as e:
        return {
            "answer": f"文档检索或 Rerank 失败：{e}",
            "retrieval_question": "",
            "candidate_docs_with_scores": [],
            "retrieved_docs_with_scores": [],
            "top_k": 0,
            "candidate_top_n": 0,
            "rerank_used": False,
            "error": str(e),
        }


def should_continue_to_rag_answer(state: AgentState) -> Literal["rag_answer_node", "end"]:
    """
    检索后判断是否继续生成 RAG 答案。

    如果检索阶段已经产生错误答案，就直接结束。
    """
    answer = state.get("answer", "")
    error = state.get("error", "")

    if answer and error:
        return "end"

    return "rag_answer_node"


def unpack_rag_answer_result(result: Any) -> Dict[str, Any]:
    """
    兼容不同版本 generate_answer_with_sources 的返回格式。

    你之前的版本大概率返回：
    answer, validation_result, was_repaired
    """
    if isinstance(result, tuple):
        if len(result) == 3:
            answer, validation_result, was_repaired = result
            return {
                "answer": answer,
                "validation_result": validation_result,
                "was_repaired": was_repaired,
            }

        if len(result) == 2:
            answer, validation_result = result
            return {
                "answer": answer,
                "validation_result": validation_result,
                "was_repaired": False,
            }

        if len(result) == 1:
            return {
                "answer": result[0],
                "validation_result": {},
                "was_repaired": False,
            }

    if isinstance(result, dict):
        return {
            "answer": result.get("answer", ""),
            "validation_result": result.get("validation_result", {}),
            "was_repaired": result.get("was_repaired", False),
        }

    return {
        "answer": str(result),
        "validation_result": {},
        "was_repaired": False,
    }


def rag_answer_node(state: AgentState) -> Dict[str, Any]:
    """
    RAG 回答节点。

    数学错题卡模式开启时：
    - 不走普通 Markdown 回答
    - 直接生成 math_items
    - answer 保存 JSON 字符串
    """
    question = state.get("question", "")
    chat_history = state.get("chat_history", [])
    task_info = state.get("task_info", {})
    retrieved_docs_with_scores = state.get("retrieved_docs_with_scores", [])

    if not retrieved_docs_with_scores:
        return {
            "answer": "没有检索到足够相关的资料片段，请检查文档是否已成功解析，或换一种问法重新提问。",
            "validation_result": {
                "valid": False,
                "errors": ["retrieved_docs_with_scores is empty"],
                "items": [],
            },
            "was_repaired": False,
            "math_question_type": "",
            "math_items": [],
            "stat_question_type": "",
            "stat_items": [],
            "error": "retrieved_docs_with_scores is empty",
        }

    try:
        if getattr(config, "ENABLE_MATH_EXAM_MODE", False):
            result = generate_math_exam_answer(
                question=question,
                task_info=task_info,
                retrieved_docs_with_scores=retrieved_docs_with_scores,
                chat_history=chat_history,
            )

            return {
                "answer": result.get("answer", ""),
                "validation_result": result.get("validation_result", {}),
                "was_repaired": result.get("was_repaired", False),
                "math_question_type": result.get("question_type", ""),
                "math_items": result.get("items", []),

                # 兼容旧 app.py
                "stat_question_type": result.get("question_type", ""),
                "stat_items": result.get("items", []),

                "error": "",
            }

        # 关闭数学模式时，回退到原来的通用 RAG 回答
        try:
            result = generate_answer_with_sources(
                question=question,
                task_info=task_info,
                retrieved_docs_with_scores=retrieved_docs_with_scores,
                chat_history=chat_history,
            )
        except TypeError:
            try:
                result = generate_answer_with_sources(
                    question,
                    task_info,
                    retrieved_docs_with_scores,
                    chat_history,
                )
            except TypeError:
                result = generate_answer_with_sources(
                    question,
                    task_info,
                    retrieved_docs_with_scores,
                )

        if isinstance(result, dict):
            return {
                "answer": result.get("answer", ""),
                "validation_result": result.get("validation_result", {}),
                "was_repaired": result.get("was_repaired", False),
                "math_question_type": "",
                "math_items": [],
                "stat_question_type": "",
                "stat_items": [],
                "error": "",
            }

        if isinstance(result, tuple):
            if len(result) == 3:
                answer, validation_result, was_repaired = result
            elif len(result) == 2:
                answer, validation_result = result
                was_repaired = False
            else:
                answer = str(result[0])
                validation_result = {}
                was_repaired = False

            return {
                "answer": answer,
                "validation_result": validation_result,
                "was_repaired": was_repaired,
                "math_question_type": "",
                "math_items": [],
                "stat_question_type": "",
                "stat_items": [],
                "error": "",
            }

        return {
            "answer": str(result),
            "validation_result": {},
            "was_repaired": False,
            "math_question_type": "",
            "math_items": [],
            "stat_question_type": "",
            "stat_items": [],
            "error": "",
        }

    except Exception as e:
        return {
            "answer": f"生成数学题目解析答案时出错：{e}",
            "validation_result": {
                "valid": False,
                "errors": [str(e)],
                "items": [],
            },
            "was_repaired": False,
            "math_question_type": "",
            "math_items": [],
            "stat_question_type": "",
            "stat_items": [],
            "error": str(e),
        }


def build_agent_graph():
    """
    构建 LangGraph 工作流。
    """
    graph = StateGraph(AgentState)

    graph.add_node("router_node", router_node)
    graph.add_node("tool_node", tool_node)
    graph.add_node("direct_answer_node", direct_answer_node)
    graph.add_node("rag_retrieval_node", rag_retrieval_node)
    graph.add_node("rag_answer_node", rag_answer_node)

    graph.add_edge(START, "router_node")

    graph.add_conditional_edges(
        "router_node",
        route_after_router,
        {
            "tool_node": "tool_node",
            "direct_answer_node": "direct_answer_node",
            "rag_retrieval_node": "rag_retrieval_node",
        },
    )

    graph.add_edge("tool_node", END)
    graph.add_edge("direct_answer_node", END)

    graph.add_conditional_edges(
        "rag_retrieval_node",
        should_continue_to_rag_answer,
        {
            "rag_answer_node": "rag_answer_node",
            "end": END,
        },
    )

    graph.add_edge("rag_answer_node", END)

    return graph.compile()


_AGENT_GRAPH = None


def get_agent_graph():
    """
    获取已编译的 Graph，避免每次提问都重新 compile。
    """
    global _AGENT_GRAPH

    if _AGENT_GRAPH is None:
        _AGENT_GRAPH = build_agent_graph()

    return _AGENT_GRAPH


def run_agent_graph(
    question: str,
    chat_history=None,
    vector_db=None,
    chunks=None,
) -> AgentState:
    """
    给 app.py 调用的统一入口。
    """
    if chat_history is None:
        chat_history = []

    if chunks is None:
        chunks = []

    graph = get_agent_graph()

    input_state: AgentState = {
        "question": question,
        "chat_history": chat_history,
        "vector_db": vector_db,
        "chunks": chunks,
        "task_info": {},
        "route": "",
        "tool_result": {},
        "retrieval_question": "",
        "candidate_docs_with_scores": [],
        "candidate_top_n": 0,
        "retrieved_docs_with_scores": [],
        "rerank_used": False,
        "answer": "",
        "validation_result": {},
        "was_repaired": False,
        "error": "",
        "math_question_type": "",
        "math_items": [],
    }

    start_time = time.time()

    try:
        result = graph.invoke(input_state)
        result["elapsed_seconds"] = round(time.time() - start_time, 4)
        return result

    except Exception as e:
        return {
            **input_state,
            "answer": f"LangGraph 工作流运行失败：{e}",
            "error": str(e),
            "elapsed_seconds": round(time.time() - start_time, 4),
        }
