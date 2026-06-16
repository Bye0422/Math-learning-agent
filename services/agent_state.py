from typing import Any, Dict, List, Tuple, TypedDict

from langchain_core.documents import Document


class AgentState(TypedDict, total=False):
    """
    LangGraph 共享状态。
    total=False 表示字段不是每一步都必须存在。
    """

    # 用户输入
    question: str
    chat_history: List[Dict[str, str]]

    # Router 结果
    task_info: Dict[str, Any]
    route: str

    # Tool 调用结果
    tool_result: Dict[str, Any]

    # RAG 检索相关
    vector_db: Any
    chunks: List[Document]
    top_k: int

    retrieval_question: str

    # Hybrid Retrieval 初筛候选
    candidate_docs_with_scores: List[Tuple[Document, float]]
    candidate_top_n: int

    # Rerank 后最终片段
    retrieved_docs_with_scores: List[Tuple[Document, float]]
    rerank_used: bool

    # 通用回答
    answer: str
    validation_result: Dict[str, Any]
    was_repaired: bool

    # 数学题目解析结构化输出
    math_question_type: str
    math_items: List[Dict[str, Any]]

    # 兼容旧统计学字段，避免 app.py 旧代码报错
    stat_question_type: str
    stat_items: List[Dict[str, Any]]

    # 运行信息
    error: str
    elapsed_seconds: float