def build_task_classification_prompt(question, history_text):
    return f"""
你是一个 Agent 任务识别器。

请根据历史对话和用户当前问题，判断用户想完成什么任务。

任务类型只能从下面选择一个：
1. qa：普通文档问答，例如“这个概念是什么意思”“这段话说明了什么”
2. summary：文档总结，例如“总结这个文件”“概括主要内容”
3. extract_points：提取知识点，例如“提取知识点”“列出重点”“整理考点”
4. question_solving：题目解析，例如“这道题怎么做”“为什么选A”“计算题怎么解”
5. format_answer：固定格式输出，例如“按选择题格式输出”“按表格输出”“生成固定模板答案”
6. chit_chat：闲聊或与文档无关，例如“你好”“你能做什么”
7. calculation：纯数学计算或公式运算，例如“计算 1.96 * 2.5 / sqrt(100)”“帮我算 3*5+2”
8. log_query：查询系统运行日志，例如“刚刚检索到了哪些 chunk”“刚才耗时多少”“刚刚任务类型是什么”“刚才有没有触发修复”

判断规则：
- 如果用户只是要求计算一个明确数学表达式，选择 calculation，need_rag=false。
- 如果用户询问刚刚、上一次、最近一次运行情况、检索片段、耗时、日志、任务类型、是否修复，选择 log_query，need_rag=false。
- 如果用户问的是文档里的题目怎么做，即使涉及计算，也优先选择 question_solving，need_rag=true。
- 如果用户要求根据上传文档回答，选择对应的 RAG 任务，need_rag=true。
- 如果用户只是闲聊或问系统能力，选择 chit_chat，need_rag=false。

请只输出 JSON，不要输出解释，不要使用 Markdown。

JSON 格式如下：
{{
  "task_type": "qa",
  "need_rag": true,
  "answer_format": "普通问答",
  "reason": "用户在询问文档内容"
}}

【历史对话】
{history_text}

【用户当前问题】
{question}
"""