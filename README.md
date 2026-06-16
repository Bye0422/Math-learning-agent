## 项目名称

基于 LangGraph 的多模态 RAG 数学学习Agent

## 项目简介

本项目是一个面向 PDF、Word、TXT、图片等多格式文件的 RAG Agent 文档问答系统，支持文档解析、MinerU 数学公式 PDF 解析、图片 OCR、文本切分、向量检索、Hybrid Retrieval、LLM Rerank、多轮问答、Tool Calling、LangGraph 工作流编排、Guardrails 输出校验、SQLite Memory、日志追踪、Eval 自动评估以及 Word / TXT 结果导出。

项目围绕真实 LLM 应用开发流程设计，不只是简单调用大模型 API，而是从文档输入、解析清洗、知识库构建、检索增强生成，到工具调用、工作流编排、结果校验、持久化记忆和评估体系，构建了一套较完整的 Agent 工程实践链路。

## 核心功能

### 1. 多格式文档解析

系统支持 PDF、Word、TXT、图片等多种输入格式。不同格式的文件会被统一转换为 LangChain Document 对象，随后进入 chunk 切分、embedding、向量检索和 RAG 问答流程。

PDF 文件优先使用 MinerU 进行解析，适合处理数学公式、复杂排版、真题资料等传统 pypdf 容易乱码或公式丢失的文档。图片文件通过千问多模态模型进行 OCR 识别。

### 2. MinerU 数学公式 PDF 解析优化

针对数学公式 PDF 解析慢、易失败、重复解析成本高的问题，系统对 MinerU 接入做了多项工程优化：

* 使用英文路径作为 MinerU 临时运行目录，减少 Windows 中文路径兼容问题。
* 使用 `auto` 模式解析数学公式 PDF，避免将非扫描版 PDF 强制 OCR。
* 支持大 PDF 按页分批解析，降低单次解析失败率。
* 对 MinerU 输出的 Markdown 进行清洗，去除页码、重复页眉页脚等噪声。
* 基于文件 hash 建立 MinerU Markdown 缓存，同一 PDF 第二次上传时可直接读取缓存，减少重复解析成本。
* 增加 PDF 解析质量评分，从文本长度、乱码比例、空行比例、题号保留、选项结构、数学公式符号等维度判断解析质量。

### 3. RAG 检索问答

系统使用 `text-embedding-v4` 对文档 chunk 进行向量化，并使用 Chroma 作为向量数据库。用户提问后，系统会根据问题类型和历史对话改写检索问题，再进行文档检索和回答生成。

基础链路如下：

```text
上传文件
→ 文档解析
→ Markdown 清洗
→ PDF 质量评分
→ Document
→ Chunk
→ Embedding
→ Chroma
→ Hybrid Retrieval
→ LLM Rerank
→ RAG Answer
→ Guardrails
→ 最终回答
```

### 4. Hybrid Retrieval 混合检索

系统在普通向量检索基础上加入规则检索，支持题号、题型、关键词等信息的精确匹配。对于“第一题怎么做”“第 2 题的解题思路是什么”这类问题，规则检索可以弥补纯向量检索对题号、编号、公式和短文本定位不稳定的问题。

### 5. LLM Rerank 重排序

系统在 Hybrid Retrieval 初筛之后，引入 LLM Rerank 模块。流程为：

```text
Hybrid Retrieval 召回多个候选 chunk
→ LLM 对每个 chunk 进行 0-5 分相关性评分
→ 按分数重新排序
→ 选择最相关的 chunk 进入回答生成
```

该模块可以提高数学题、公式类文档、题号定位场景下的上下文命中准确性。

### 6. LangGraph 工作流编排

项目使用 LangGraph 对 Agent 流程进行编排，将原本写在 `app.py` 中的判断逻辑拆分为多个节点：

```text
router_node
→ tool_node / direct_answer_node / rag_retrieval_node
→ rag_answer_node
→ END
```

其中 Router 节点负责识别任务类型，条件边根据任务类型决定进入工具调用、直接回答或 RAG 检索问答流程。通过 LangGraph，系统从普通 if/else 控制流程升级为显式 Agent Workflow。

### 7. Tool Calling 与 Tool Registry

项目实现了工具调用机制，并通过 Tool Registry 对工具进行统一注册和调用。目前包含：

* 计算器工具：用于执行确定性数学表达式计算。
* 日志查询工具：用于读取最近一次 Agent 运行日志。

模型不再直接“心算”或猜测运行状态，而是由 Agent 判断任务类型后调用对应工具完成任务。

### 8. Guardrails 输出校验

系统会根据任务类型对模型输出进行结构化校验。例如题目解析任务要求包含：

```text
答案
解题思路
详细解析
依据来源
```

如果回答格式不合格，系统会自动调用修复 Prompt，在不新增事实、不改变原意的前提下整理回答格式。

### 9. SQLite Memory 持久化记忆

系统引入 SQLite Memory，保存 session 级历史问答，包括用户问题、AI 回答、任务类型、路由结果、检索问题、Rerank 状态、检索来源、格式校验结果和执行耗时等信息。相比只依赖 Streamlit session_state，SQLite Memory 可以在页面刷新或重新打开后恢复历史会话。

### 10. 日志追踪

系统将每轮 Agent 运行过程写入 CSV 日志，记录任务识别、检索问题、命中 chunk、Rerank 状态、格式校验、自动修复、耗时和错误信息，便于调试和问题追踪。

### 11. Eval V2 自动评估体系

项目构建了 Eval V2 自动评估体系，覆盖以下能力：

* LangGraph 路由准确率
* 任务识别准确率
* 是否需要 RAG 判断准确率
* Tool Calling 是否成功
* RAG 检索命中率
* 答案关键词命中率
* 必需字段完整率
* Guardrails 格式合规率
* Rerank 使用率与平均评分
* 平均响应耗时
* PDF 解析质量信息
* SQLite Memory 写入检查

通过 Eval V2，系统不再只依赖人工试用，而是可以用量化指标评估 Agent 效果。

## 技术栈

| 模块        | 技术                                       |
| --------- | ---------------------------------------- |
| 前端界面      | Streamlit                                |
| 大模型调用     | Qwen API，OpenAI Compatible API           |
| OCR       | Qwen 多模态模型                               |
| PDF 增强解析  | MinerU                                   |
| PDF 回退解析  | pypdf                                    |
| Word 解析   | python-docx                              |
| 文本切分      | LangChain RecursiveCharacterTextSplitter |
| Embedding | text-embedding-v4                        |
| 向量数据库     | Chroma                                   |
| 混合检索      | Vector Retrieval + Rule Retrieval        |
| Rerank    | LLM Rerank                               |
| Agent 编排  | LangGraph                                |
| 工具调用      | Tool Registry                            |
| 输出校验      | 自定义 Guardrails                           |
| 记忆机制      | SQLite                                   |
| 日志追踪      | CSV                                      |
| 评估体系      | Eval V2                                  |
| 结果导出      | TXT / Word                               |

## 项目亮点

1. 针对数学公式 PDF 场景，引入 MinerU 解析、Markdown 清洗、分批解析、缓存复用和质量评分，提高复杂 PDF 在 RAG 系统中的可用性。
2. 在检索链路中结合 Hybrid Retrieval 与 LLM Rerank，兼顾语义召回和题号、关键词、公式等精确定位能力。
3. 使用 LangGraph 将 Router、Tool、RAG、Answer 等流程节点化，实现显式 Agent Workflow。
4. 实现 Tool Registry，将计算器工具、日志查询工具等统一注册和调度，减少 app.py 中的硬编码分支。
5. 引入 Guardrails 输出校验与自动修复机制，提高题目解析、知识点提取、格式化输出等任务的稳定性。
6. 使用 SQLite Memory 保存 session 级历史问答，实现会话持久化和历史追踪。
7. 构建 Eval V2 自动评估体系，从任务识别、路由、检索、Rerank、格式合规、耗时等维度量化系统效果。

## 当前不足与后续优化

当前项目仍有以下可优化方向：

1. 引入专门的 reranker 模型，替代 LLM Rerank，降低重排序成本并提升稳定性。
2. 对 MinerU 输出的结构化 JSON 进行更精细解析，进一步过滤页眉、页脚、页码等版面噪声。
3. 增加更多数学公式 PDF、真题 PDF 和复杂版式文档的 Eval 样本，提高评估覆盖率。
4. 增加历史会话列表和会话切换功能，使 SQLite Memory 更接近真实产品体验。
5. 使用 Docker 或云服务器部署系统，支持在线访问。
6. 对批量题目解析结果增加 Excel 结构化导出能力。

## 学习收获

通过本项目，完成了从基础 LLM API 调用到完整 RAG Agent 工程的学习，覆盖：

```text
Prompt 设计
多格式文档解析
MinerU PDF 解析
Markdown 清洗
PDF 解析缓存
PDF 质量评分
OCR
Chunk 切分
Embedding
向量数据库
Hybrid Retrieval
LLM Rerank
RAG 检索问答
Tool Calling
Tool Registry
LangGraph
Guardrails
Eval
SQLite Memory
日志追踪
结果导出
模块化工程结构
```

本项目适合作为 LLM 应用开发、RAG 系统开发、Agent 工程实践方向的学习项目。
