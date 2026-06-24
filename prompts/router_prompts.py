def build_task_classification_prompt(question, history_text):
    return f"""
你是一个 Agent 任务识别器。

请根据历史对话和用户当前问题，判断用户想完成什么任务。

任务类型只能从下面选择一个：
1. qa：普通文档问答，例如“这个概念是什么意思”“这段话说明了什么”
2. summary：文档总结，例如“总结这个文件”“概括主要内容”
3. extract_points：提取知识点，例如“提取知识点”“列出重点”“整理考点”
4. question_solving：需要结合上传资料、图片、试卷题号或文档内容进行题目解析
5. format_answer：固定格式输出，例如“按选择题格式输出”“按表格输出”
6. chit_chat：闲聊或与文档无关的问题
7. calculation：不需要上传资料即可回答的数学计算、公式运算或数学求解
8. log_query：查询系统运行日志，例如“刚刚检索到了哪些 chunk”“刚才耗时多少”

calculation 包括但不限于：
- 普通数值计算、百分数、分数、根式、幂、三角函数；
- 表达式化简、展开、因式分解；
- 积分、导数、偏导、极限、求和；
- 方程、方程组、不等式；
- 矩阵加减、乘法、转置、逆、行列式、秩、特征值；
- 概率和统计中的直接计算。

判断规则：
- 用户使用自然语言描述计算，也选择 calculation，例如“二十三乘四”“求 x 从 0 到 1 的积分”“x 趋近 0 时 sin(x)/x 的极限”。
- 用户要求步骤、详细过程、验证结果，也仍然选择 calculation。
- calculation 一律设置 need_rag=false，由大模型直接理解问题并给出结果，不调用计算工具。
- 用户明确引用上传资料、图片、试卷题号或文档内容时，选择 question_solving，need_rag=true。
- 用户只是询问某个数学原理、公式为什么成立，但不依赖上传资料时，选择 question_solving，need_rag=false。
- log_query 设置 need_rag=false，并继续使用日志工具。
- chit_chat 设置 need_rag=false。

请只输出 JSON，不要输出解释，不要使用 Markdown。

JSON 格式如下：
{{
  "task_type": "calculation",
  "need_rag": false,
  "answer_format": "数学解答",
  "reason": "用户要求直接完成数学计算"
}}

【历史对话】
{history_text}

【用户当前问题】
{question}
"""
