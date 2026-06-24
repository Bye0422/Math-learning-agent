# Math-learning-agent

一个面向数学学习场景的 Streamlit Agent。它既可以作为日常陪伴式聊天助手，也可以在用户上传资料后进行题目解析、资料检索、Chunk 校正、错题卡生成、错题库管理和 PDF 导出。

## 功能概览

- 日常对话：支持普通聊天、情绪陪伴、学习建议和直接问答。
- 资料问答：上传 PDF、DOCX、TXT、PNG、JPG、JPEG、WEBP 后建立向量库，再基于资料回答。
- 数学题解析：针对“第几题”“课后习题 3.1 第二题”等引用，结合规则检索、向量检索和 Rerank 定位资料片段。
- Chunk 校正：查看并修正资料解析后的片段，提升后续检索质量。
- 错题卡：用户确认后再生成错题卡，支持修改解析、难度、题型和标签。
- 错题库：持久化保存错题，支持筛选、复习状态管理和选中导出 PDF。
- 本地记忆：SQLite 保存会话历史和错题数据，运行数据默认不提交到 Git。

## 技术栈

- UI：Streamlit
- Agent 编排：LangGraph
- LLM 接入：OpenAI-compatible API，默认面向通义千问 DashScope
- 检索：LangChain + Chroma + 规则检索 + LLM Rerank
- 文档解析：MinerU 优先，pypdf 兜底；DOCX、TXT、图片 OCR
- 持久化：SQLite
- 卡片/PDF：HTML + MathJax + Playwright 截图，Pillow/ReportLab/PDF 导出

## 快速开始

### 1. 创建虚拟环境

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

### 2. 安装依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果需要错题卡 HTML 截图能力，还需要安装 Playwright Chromium：

```powershell
.\.venv\Scripts\playwright.exe install chromium
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，填写你的模型配置：

```powershell
Copy-Item .env.example .env
```

至少需要配置：

```env
QWEN_API_KEY=replace-with-your-api-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_CHAT_MODEL=qwen3.7-plus
QWEN_OCR_MODEL=qwen-vl-ocr
QWEN_EMBEDDING_MODEL=text-embedding-v4
```

说明：

- `QWEN_CHAT_MODEL` 用于路由、聊天、解析和 RAG 生成。
- `QWEN_OCR_MODEL` 用于图片 OCR，必须是支持视觉输入的模型。
- `QWEN_EMBEDDING_MODEL` 用于构建 Chroma 向量库。
- `.env` 已被 `.gitignore` 忽略，不要提交密钥。

### 4. 启动应用

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

也可以使用启动脚本：

```powershell
.\scripts\start.ps1
```

默认访问地址通常是：

```text
http://localhost:8501
```

## 使用流程

1. 直接在对话区提问，可以聊天、询问学习建议、做简单计算或缓解情绪。
2. 需要基于资料解析时，打开资料入口上传文件，等待系统建立向量库。
3. 提问类似“第 2 题怎么做”“课后习题 3.1 第二题怎么做”。
4. 系统先返回解析答案，不会自动生成错题卡。
5. 用户点击生成错题卡后，再进入错题卡修改、导入错题库、错题库筛选和 PDF 导出流程。

## 项目结构

```text
.
├─ app.py                         # Streamlit 页面、交互和业务入口
├─ config.py                      # 配置和环境变量
├─ prompts/                       # 路由、检索、解析、OCR、校验 Prompt
├─ services/                      # 文档解析、检索、Agent、错题库、导出等服务
│  └─ tools/                      # 工具任务路由和日志查询回退
├─ state/                         # Streamlit session state 初始化
├─ ui/                            # 主题样式、结果视图、Chunk 调试面板
├─ validators/                    # 任务分类和模型输出校验
├─ tests/                         # 离线单元测试
├─ evals/                         # RAG/Agent 评估脚本
├─ scripts/                       # 启动、环境检查、测试 Harness、清理脚本
├─ data/                          # 运行时数据库、卡片和导出文件，不提交
├─ cache/                         # 向量库和 MinerU 缓存，不提交
├─ logs/                          # 运行日志，不提交
├─ mineru_runtime/                # MinerU 临时目录，不提交
├─ Dockerfile
├─ DEPLOYMENT.md
└─ requirements.txt
```

## 核心模块

- `services/agent_graph.py`：LangGraph 工作流。Router 判断任务后分流到 direct、tool 或 RAG。
- `services/rag_service.py`：任务分类、检索问题改写、直接回答和 RAG 回答。
- `services/retrieval_service.py`：混合检索。支持题号、章节号、习题号等规则命中，再与向量检索合并排序。
- `services/vector_service.py`：文档切分、题目优先 Chunk、Chroma 向量库创建和缓存。
- `services/document_loader.py`：PDF/DOCX/TXT/图片解析。PDF 优先 MinerU，失败后回退 pypdf。
- `services/math_exam_service.py`：数学解析生成，读取 `prompts/KAFANG_MODEL_PROMPT.md` 和 `prompts/KAFANG_VALIDATION_PROMPT.md`。
- `services/wrongbook_service.py`：错题库 SQLite、筛选、复习状态和 PDF 导出。
- `ui/theme.py`：主要视觉样式。

## 验证

快速验证：

```powershell
.\.venv\Scripts\python.exe scripts\run_harness.py --mode quick
```

它会执行：

- Python 语法检查
- `tests/` 单元测试
- 环境和关键依赖检查

完整启动验证：

```powershell
.\.venv\Scripts\python.exe scripts\run_harness.py --mode full --port 8501
```

如果需要运行 Eval V2：

```powershell
.\.venv\Scripts\python.exe scripts\run_harness.py --mode full --eval
```

Eval 可能调用真实模型 API。需要评估资料时，把文档放到 `evals/source_docs/`，该目录默认只保留 `.gitkeep`。

## 运行数据和 GitHub 提交

以下内容是本地运行产物，默认不会提交：

- `.env`
- `.venv/`
- `.codex/`
- `.agents/`
- `data/`
- `cache/`
- `logs/`
- `mineru_runtime/`
- `__pycache__/`
- `evals/source_docs/*`

上传 GitHub 前建议检查：

```powershell
git status --short
git ls-files --others --exclude-standard
```

## Docker

构建镜像：

```powershell
docker build -t math-learning-agent .
```

运行示例：

```powershell
docker run --rm -p 8501:8501 --env-file .env math-learning-agent
```

如果在容器中需要 Playwright 截图功能，需要在镜像层安装 Chromium 浏览器二进制。更多部署说明见 `DEPLOYMENT.md`。

## 常见问题

### 图片无法 OCR

确认 `QWEN_OCR_MODEL` 是支持视觉输入的模型，并且 DashScope API Key 有对应模型权限。

### 上传 PDF 后内容不完整

优先检查 MinerU 是否可用：

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
```

如果 MinerU 不可用，系统会回退到 pypdf，但数学公式和扫描版 PDF 的效果可能变差。

### 问“第几题”时找不到题目

先确认资料已上传并建立向量库。系统支持“第 2 题”“3.1 的第二题”“课后习题 1.1 中第二题”等引用，但资料本身需要在解析后保留题号或章节信息。

### PDF 导出失败

错题 PDF 导出依赖已生成的错题卡图片。请先生成错题卡并导入错题库，再在错题库中选择导出。

## 开发建议

- 普通修改跑 `scripts/run_harness.py --mode quick`。
- UI、启动、部署相关修改跑 `--mode full`。
- RAG、Prompt、Router、检索相关修改可以补充 Eval V2。
- 不要提交 `.env`、数据库、向量库、缓存、日志或用户资料。
