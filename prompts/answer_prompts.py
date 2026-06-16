ANSWER_FORMATS = {
    "summary": """
请按下面格式回答：

文档主题：
……

核心内容：
1. ……
2. ……
3. ……

关键结论：
……

依据来源：
- 资料片段 X：文件名，文件类型，位置，Chunk X
""",

    "extract_points": """
请按下面格式回答：

知识点整理：
1. ……
2. ……
3. ……

重点解释：
- ……
- ……

适合复习的提示：
……

依据来源：
- 资料片段 X：文件名，文件类型，位置，Chunk X
""",

    "question_solving": """
请按下面格式回答：

答案：
……

解题思路：
……

详细解析：
……

易错点：
……

依据来源：
- 资料片段 X：文件名，文件类型，位置，Chunk X
""",

    "format_answer": """
请按用户要求的格式输出。
如果用户没有明确格式，请按下面格式回答：

结果：
……

说明：
……

依据来源：
- 资料片段 X：文件名，文件类型，位置，Chunk X
""",

    "qa": """
请按下面格式回答：

答案：
……

理由：
……

依据来源：
- 资料片段 X：文件名，文件类型，位置，Chunk X
"""
}


def build_context_from_docs(docs):
    context_parts = []

    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "未知文件")
        file_type = doc.metadata.get("file_type", "未知类型")
        location = doc.metadata.get("location", "未知位置")
        chunk_id = doc.metadata.get("chunk_id", "未知片段")

        context_parts.append(
            f"""【资料片段 {i}】
来源：{source}
类型：{file_type}
位置：{location}
Chunk：{chunk_id}
内容：
{doc.page_content}
"""
        )

    return "\n\n".join(context_parts)


def build_rag_answer_prompt(question, docs, history_text, task_info):
    context = build_context_from_docs(docs)

    task_type = task_info.get("task_type", "qa")
    answer_format = task_info.get("answer_format", "")
    reason = task_info.get("reason", "")

    format_instruction = ANSWER_FORMATS.get(task_type, ANSWER_FORMATS["qa"])

    return f"""
你是一个严谨的多格式多轮 RAG Agent。

你需要根据任务类型选择合适的回答方式。

【任务识别结果】
任务类型：{task_type}
回答格式：{answer_format}
识别原因：{reason}

【历史对话】
{history_text}

【资料】
{context}

【用户当前问题】
{question}

【通用要求】
1. 必须优先根据资料片段回答。
2. 如果资料中没有明确答案，请回答：资料中没有找到相关信息。
3. 不要编造资料中没有的内容。
4. 可以参考历史对话理解“它”“这个”“为什么不是”等指代。
5. 最终答案必须写“依据来源”。
6. 依据来源必须写清楚资料片段编号、文件名、文件类型、位置和 Chunk 编号。

{format_instruction}
"""