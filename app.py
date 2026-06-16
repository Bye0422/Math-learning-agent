import uuid
from datetime import datetime

import streamlit as st

from config import (
    APP_PAGE_TITLE,
    APP_TITLE,
    SUPPORTED_FILE_TYPES,
    EXPORT_FILE_PREFIX,
    ENABLE_SQLITE_MEMORY,
    MEMORY_DB_PATH,
    MEMORY_HISTORY_LIMIT,
    PRODUCT_NAME,
    PRODUCT_CHINESE_NAME,
    ENABLE_MATH_EXAM_MODE,
    ENABLE_WRONGBOOK,
)

from services.agent_graph import run_agent_graph

from services.llm_service import check_env
from services.document_loader import read_multiple_files_to_documents
from services.vector_service import (
    split_documents,
    create_vector_db,
)

from services.log_service import (
    LOG_FILE,
    ensure_log_file,
    write_agent_log,
    build_retrieved_sources,
)

from services.export_service import (
    build_export_text,
    build_export_docx_bytes,
)

from services.memory_service import (
    init_memory_db,
    load_chat_history,
    save_qa_turn,
    clear_session_memory,
    get_recent_sessions,
)

from services.card_render_service import (
    infer_question_text_for_card,
    build_source_info,
)

from services.card_html_render_service import (
    render_html_cards_for_items,
)

from services.wrongbook_service import (
    init_wrongbook_db,
    save_wrong_question_cards,
    get_wrong_questions,
    count_wrong_questions,
    export_wrong_questions_to_pdf,
)

from services.card_edit_service import (
    build_item_from_user_edit,
    edit_card_with_llm,
)

# =========================
# 页面设置
# =========================

st.set_page_config(page_title=APP_PAGE_TITLE, layout="wide")
st.title(APP_TITLE)

if ENABLE_MATH_EXAM_MODE:
    st.caption(
        "面向小学到大学的数学题目，支持上传 PDF、Word、TXT、图片或直接输入题干，"
        "自动生成题干、解析、难度星级、题目类型和知识点标签，并可加入错题库、导出 PDF 错题集。"
    )


# =========================
# UI 函数：导出按钮
# =========================

def render_export_buttons():
    chat_history = st.session_state.get("chat_history", [])
    file_names = st.session_state.get("current_file_names", [])
    session_id = st.session_state.get("session_id", "")
    last_log_row = st.session_state.get("last_log_row")

    if not chat_history:
        st.info("暂无问答记录，完成至少一轮问答后可导出。")
        return

    export_text = build_export_text(
        chat_history=chat_history,
        file_names=file_names,
        session_id=session_id,
        last_log_row=last_log_row,
    )

    export_docx = build_export_docx_bytes(
        chat_history=chat_history,
        file_names=file_names,
        session_id=session_id,
        last_log_row=last_log_row,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    st.download_button(
        label="下载 TXT 问答结果",
        data=export_text.encode("utf-8-sig"),
        file_name=f"{EXPORT_FILE_PREFIX}_{timestamp}.txt",
        mime="text/plain",
    )

    st.download_button(
        label="下载 Word 问答结果",
        data=export_docx,
        file_name=f"{EXPORT_FILE_PREFIX}_{timestamp}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# =========================
# UI 函数：PDF 质量检测展示
# =========================

def render_pdf_quality_result(documents):
    """
    在页面展示 PDF 解析质量检测结果。
    """
    quality_docs = []

    for doc in documents:
        metadata = doc.metadata or {}

        if metadata.get("pdf_quality_score", "") != "":
            quality_docs.append(doc)

    if not quality_docs:
        return

    st.subheader("PDF 解析质量检测")

    for index, doc in enumerate(quality_docs, start=1):
        metadata = doc.metadata or {}

        source = metadata.get("source", "")
        file_type = metadata.get("file_type", "")
        score = metadata.get("pdf_quality_score", "")
        level = metadata.get("pdf_quality_level", "")
        issues = metadata.get("pdf_quality_issues", "")
        suggestions = metadata.get("pdf_quality_suggestions", "")

        title = f"{source} | {level} | {score} 分"

        if level == "good":
            st.success(f"解析质量：{title}")
        elif level == "medium":
            st.warning(f"解析质量：{title}")
        else:
            st.error(f"解析质量：{title}")

        with st.expander(f"查看质量检测详情 {index}"):
            st.write(f"来源文件：{source}")
            st.write(f"文件类型：{file_type}")
            st.write(f"质量等级：{level}")
            st.write(f"质量分数：{score}")

            st.write("主要问题：")
            st.write(issues)

            st.write("优化建议：")
            st.write(suggestions)

            st.write("检测指标：")
            st.write(
                {
                    "文本长度": metadata.get("pdf_quality_text_length", ""),
                    "乱码比例": metadata.get("pdf_quality_garbled_ratio", ""),
                    "空行比例": metadata.get("pdf_quality_blank_line_ratio", ""),
                    "正文密度": metadata.get("pdf_quality_content_density", ""),
                    "题号数量": metadata.get("pdf_quality_question_count", ""),
                    "选项数量": metadata.get("pdf_quality_option_count", ""),
                    "数学符号数量": metadata.get("pdf_quality_math_token_count", ""),
                    "公式行数量": metadata.get("pdf_quality_formula_line_count", ""),
                    "重复短行数量": metadata.get("pdf_quality_repeated_short_line_count", ""),
                }
            )


# =========================
# UI 函数：数学结构化解析展示
# =========================

def render_math_exam_items(items):
    """
    展示数学题目解析结构化结果。
    每道题必须包含 analysis、difficulty、type、tags。
    """
    if not items:
        return

    st.subheader("数学题目解析结果")

    for index, item in enumerate(items, start=1):
        analysis = item.get("analysis", "")
        difficulty = item.get("difficulty", "")
        question_type = item.get("type", "")
        tags = item.get("tags", [])

        with st.expander(
            f"第 {index} 题 | {question_type} | 难度 {difficulty}",
            expanded=True,
        ):
            st.markdown("**analysis：解析**")
            st.write(analysis)

            st.markdown("**difficulty：难度**")
            st.write(difficulty)

            st.markdown("**type：题目类型**")
            st.write(question_type)

            st.markdown("**tags：标签**")
            st.json(tags)


# 兼容旧函数名，避免其他地方还在调用 render_stat_exam_items
def render_stat_exam_items(items):
    return render_math_exam_items(items)


# =========================
# UI 函数：错题卡图片展示
# =========================

def render_wrong_cards(card_results):
    """
    展示本轮生成的错题卡图片。
    """
    if not card_results:
        return

    st.subheader("错题卡片")

    for card in card_results:
        index = card.get("index", "")
        image_path = card.get("image_path", "")

        if image_path:
            st.image(
                image_path,
                caption=f"错题卡 {index}",
                use_container_width=True,
            )

# =========================
# UI 函数：错题卡编辑区
# =========================


def render_card_edit_area():
    """
    错题卡保存前编辑区。

    支持：
    1. 用户手动编辑题干、解析、难度、题型、标签。
    2. 用户输入修改要求，让 LLM 修改当前错题卡。
    3. 根据编辑后的内容重新渲染错题卡图片。
    4. 确认后加入错题库。
    """
    if not ENABLE_WRONGBOOK:
        return

    editable_items = st.session_state.get("editable_math_items", [])
    editable_question_text = st.session_state.get("editable_question_text", "")

    if not editable_items:
        return

    current_item = editable_items[0]

    st.divider()
    st.subheader("错题卡编辑与确认")

    st.info(
        "你可以直接手动编辑题干、解析、难度、题型和标签，"
        "也可以输入修改要求，让 LLM 帮你调整当前错题卡。"
    )

    # =========================
    # 让 LLM 修改
    # =========================

    with st.expander("方式一：和 LLM 沟通修改", expanded=False):
        edit_instruction = st.text_area(
            "告诉 LLM 你想怎么改",
            value=st.session_state.get("edit_instruction", ""),
            height=120,
            placeholder="例如：把解析写得更详细一点；难度改成 2；标签改成“导数, 乘积求导”。",
            key="edit_instruction_input",
        )

        if st.button("让 LLM 修改当前错题卡", key="llm_edit_current_card"):
            if not edit_instruction.strip():
                st.error("请先输入修改要求。")
            else:
                try:
                    with st.spinner("LLM 正在修改当前错题卡..."):
                        result = edit_card_with_llm(
                            question_text=editable_question_text,
                            current_item=current_item,
                            edit_instruction=edit_instruction,
                        )

                    new_question_text = result["question_text"]
                    new_items = result["items"]

                    new_card_results = render_html_cards_for_items(
                        question_text=new_question_text,
                        items=new_items,
                    )

                    st.session_state["editable_question_text"] = new_question_text
                    st.session_state["editable_math_items"] = new_items
                    st.session_state["last_card_results"] = new_card_results
                    st.session_state["last_card_saved"] = False

                    st.success("LLM 已修改错题卡，并重新生成图片。")
                    st.rerun()

                except Exception as e:
                    st.error(f"LLM 修改失败：{e}")

    # =========================
    # 用户手动编辑
    # =========================

    with st.expander("方式二：自己手动编辑", expanded=True):
        with st.form("manual_edit_card_form"):
            edited_question_text = st.text_area(
                "题干",
                value=editable_question_text,
                height=220,
            )

            edited_analysis = st.text_area(
                "解析 analysis",
                value=current_item.get("analysis", ""),
                height=260,
            )

            edited_difficulty = st.selectbox(
                "难度 difficulty",
                options=[1, 2, 3, 4, 5],
                index=max(0, min(4, int(current_item.get("difficulty", 2)) - 1)),
            )

            edited_type = st.selectbox(
                "题目类型 type",
                options=["选择题", "判断题", "简答题", "填空题", "计算题"],
                index=["选择题", "判断题", "简答题", "填空题", "计算题"].index(
                    current_item.get("type", "计算题")
                    if current_item.get("type", "计算题") in ["选择题", "判断题", "简答题", "填空题", "计算题"]
                    else "计算题"
                ),
            )

            edited_tags_text = st.text_input(
                "标签 tags",
                value=", ".join(current_item.get("tags", [])),
                help="多个标签用逗号分隔，例如：导数, 乘积求导",
            )

            submit_manual_edit = st.form_submit_button("用当前编辑内容重新生成错题卡")

        if submit_manual_edit:
            if not edited_question_text.strip():
                st.error("题干不能为空。")
            elif not edited_analysis.strip():
                st.error("解析不能为空。")
            else:
                try:
                    new_item = build_item_from_user_edit(
                        analysis=edited_analysis,
                        difficulty=edited_difficulty,
                        question_type=edited_type,
                        tags_text=edited_tags_text,
                    )

                    new_items = [new_item]

                    new_card_results = render_html_cards_for_items(
                        question_text=edited_question_text,
                        items=new_items,
                    )

                    st.session_state["editable_question_text"] = edited_question_text
                    st.session_state["editable_math_items"] = new_items
                    st.session_state["last_card_results"] = new_card_results
                    st.session_state["last_card_saved"] = False

                    st.success("已根据手动编辑内容重新生成错题卡。")
                    st.rerun()

                except Exception as e:
                    st.error(f"重新生成错题卡失败：{e}")

    # =========================
    # 当前预览
    # =========================

    current_card_results = st.session_state.get("last_card_results", [])

    if current_card_results:
        st.subheader("当前错题卡预览")
        render_wrong_cards(current_card_results)

    # =========================
    # 保存错题库
    # =========================

    st.subheader("保存到错题库")

    if st.session_state.get("last_card_saved", False):
        st.success("本轮错题卡已加入错题库。")
        return

    st.warning("确认题干、解析、难度、题型和标签无误后，再点击保存。")

    if st.button("加入错题库", key="save_edited_card_to_wrongbook"):
        try:
            saved_ids = save_wrong_question_cards(
                session_id=st.session_state.get("session_id", ""),
                card_results=st.session_state.get("last_card_results", []),
                source_info=st.session_state.get("last_card_source_info", {}),
            )

            st.session_state["last_card_saved"] = True
            st.success(f"已加入错题库，共保存 {len(saved_ids)} 道题。")
            st.rerun()

        except Exception as e:
            st.error(f"加入错题库失败：{e}")


# =========================
# 初始化 session_state
# =========================

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "vector_db" not in st.session_state:
    st.session_state["vector_db"] = None

if "current_file_key" not in st.session_state:
    st.session_state["current_file_key"] = None

if "current_file_names" not in st.session_state:
    st.session_state["current_file_names"] = []

if "documents" not in st.session_state:
    st.session_state["documents"] = []

if "chunks" not in st.session_state:
    st.session_state["chunks"] = []

if "session_id" not in st.session_state:
    st.session_state["session_id"] = uuid.uuid4().hex[:12]

if "memory_loaded" not in st.session_state:
    st.session_state["memory_loaded"] = False

if "last_log_row" not in st.session_state:
    st.session_state["last_log_row"] = None

if "last_card_results" not in st.session_state:
    st.session_state["last_card_results"] = []

if "last_card_source_info" not in st.session_state:
    st.session_state["last_card_source_info"] = {}

if "last_card_saved" not in st.session_state:
    st.session_state["last_card_saved"] = False

if "editable_question_text" not in st.session_state:
    st.session_state["editable_question_text"] = ""

if "editable_math_items" not in st.session_state:
    st.session_state["editable_math_items"] = []

if "edit_instruction" not in st.session_state:
    st.session_state["edit_instruction"] = ""


# =========================
# 启动检查
# =========================

try:
    check_env()
    ensure_log_file()

    if ENABLE_SQLITE_MEMORY:
        init_memory_db()

    if ENABLE_WRONGBOOK:
        init_wrongbook_db()

except Exception as e:
    st.error(str(e))
    st.stop()


# =========================
# 加载 SQLite Memory
# =========================

if ENABLE_SQLITE_MEMORY and not st.session_state["memory_loaded"]:
    loaded_history = load_chat_history(
        session_id=st.session_state["session_id"],
        limit=MEMORY_HISTORY_LIMIT,
    )

    if loaded_history:
        st.session_state["chat_history"] = loaded_history

    st.session_state["memory_loaded"] = True


# =========================
# 侧边栏
# =========================

with st.sidebar:
    st.subheader("运行信息")
    st.write(f"产品：`{PRODUCT_NAME}`")
    st.write(f"中文名：`{PRODUCT_CHINESE_NAME}`")
    st.write(f"Session ID：`{st.session_state['session_id']}`")
    st.write(f"日志文件：`{LOG_FILE}`")

    if st.session_state["last_log_row"]:
        with st.expander("最近一次日志"):
            st.json(st.session_state["last_log_row"])

    if ENABLE_SQLITE_MEMORY:
        st.divider()
        st.subheader("SQLite Memory")
        st.write(f"数据库：`{MEMORY_DB_PATH}`")

        if st.button("清空当前会话记忆"):
            clear_session_memory(st.session_state["session_id"])
            st.session_state["chat_history"] = []
            st.success("当前会话记忆已清空。")
            st.rerun()

        with st.expander("最近会话"):
            recent_sessions = get_recent_sessions(limit=5)

            if not recent_sessions:
                st.write("暂无历史会话。")
            else:
                for session in recent_sessions:
                    st.write("---")
                    st.write(f"Session：`{session.get('session_id', '')}`")
                    st.write(f"消息数：{session.get('message_count', 0)}")
                    st.write(f"更新时间：{session.get('updated_at', '')}")

                    file_names = session.get("file_names", [])

                    if file_names:
                        st.write("文件：")
                        for file_name in file_names[:3]:
                            st.write(f"- {file_name}")

    if ENABLE_WRONGBOOK:
        st.divider()
        st.subheader("错题库")

        total_wrong_count = count_wrong_questions()
        current_session_wrong_count = count_wrong_questions(
            session_id=st.session_state.get("session_id", "")
        )

        st.write(f"全部错题数：{total_wrong_count}")
        st.write(f"当前会话错题数：{current_session_wrong_count}")

        if st.button("导出全部错题 PDF"):
            try:
                pdf_path = export_wrong_questions_to_pdf(session_id=None)

                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="下载错题集 PDF",
                        data=f.read(),
                        file_name="wrongbook.pdf",
                        mime="application/pdf",
                    )

                st.success("错题集 PDF 已生成。")

            except Exception as e:
                st.error(f"导出失败：{e}")

        with st.expander("最近错题"):
            recent_wrong_questions = get_wrong_questions(limit=5)

            if not recent_wrong_questions:
                st.write("暂无错题。")
            else:
                for wrong in recent_wrong_questions:
                    st.write("---")
                    st.write(f"题型：{wrong.get('type', '')}")
                    st.write(f"难度：{wrong.get('difficulty', '')}")
                    st.write(f"标签：{' / '.join(wrong.get('tags', []))}")
                    st.write(f"时间：{wrong.get('created_at', '')}")

    st.divider()
    st.subheader("导出问答")
    render_export_buttons()


# =========================
# 使用说明
# =========================

if ENABLE_MATH_EXAM_MODE:
    with st.expander("我可以怎么提问？", expanded=False):
        st.write("你可以这样问：")
        st.markdown(
            """
- 第一题怎么做？
- 第 2 题为什么选 B？
- 这道函数题的解题思路是什么？
- 这道几何题容易错在哪里？
- 帮我解析这道导数题。
- 把这份试卷中的题目整理成错题卡。
- 这道概率题应该用什么公式？
- 根据这张图片生成错题卡。
            """
        )


# =========================
# 文件上传
# =========================

uploaded_files = st.file_uploader(
    "上传一个或多个文档文件",
    type=SUPPORTED_FILE_TYPES,
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("请先上传 PDF、Word、TXT 或图片文件。")
    st.stop()


current_file_names = [file.name for file in uploaded_files]
current_file_key = "|".join(
    [f"{file.name}_{file.size}" for file in uploaded_files]
)

# 换文件后，清空旧状态
if st.session_state["current_file_key"] != current_file_key:
    st.session_state["current_file_key"] = current_file_key
    st.session_state["current_file_names"] = current_file_names
    st.session_state["documents"] = []
    st.session_state["chunks"] = []
    st.session_state["vector_db"] = None
    st.session_state["chat_history"] = []
    st.session_state["last_log_row"] = None
    st.session_state["last_card_results"] = []
    st.session_state["last_card_source_info"] = {}
    st.session_state["last_card_saved"] = False
    st.session_state["editable_question_text"] = ""
    st.session_state["editable_math_items"] = []

    # 换文件时开启一个新的 session，避免不同文档的对话混在一起
    st.session_state["session_id"] = uuid.uuid4().hex[:12]
    st.session_state["memory_loaded"] = True


# =========================
# 文档解析
# =========================

if not st.session_state["documents"]:
    with st.spinner("正在解析上传文件..."):
        documents, load_errors = read_multiple_files_to_documents(uploaded_files)

    st.session_state["documents"] = documents

    for error in load_errors:
        st.warning(error)

documents = st.session_state["documents"]

if not documents:
    st.warning("没有成功读取到文档内容，请检查文件格式或重新上传。")
    st.stop()

render_pdf_quality_result(documents)

full_text = "\n\n".join([doc.page_content for doc in documents])

st.subheader("文档读取结果")
st.write(full_text[:1000])

st.success(
    f"读取完成，共读取 {len(uploaded_files)} 个文件，"
    f"共生成 {len(documents)} 个原始 Document，"
    f"共 {len(full_text)} 个字符。"
)

with st.expander("已上传文件"):
    for file_name in current_file_names:
        st.write(f"- {file_name}")


# =========================
# Chunk 切分
# =========================

if not st.session_state["chunks"]:
    chunks = split_documents(documents)
    st.session_state["chunks"] = chunks

chunks = st.session_state["chunks"]

st.subheader("文本切分结果")
st.success(f"共切分出 {len(chunks)} 个 chunk。")

with st.expander("查看前 5 个 chunk"):
    for i, chunk in enumerate(chunks[:5], start=1):
        source = chunk.metadata.get("source", "未知文件")
        file_type = chunk.metadata.get("file_type", "未知类型")
        location = chunk.metadata.get("location", "未知位置")
        chunk_id = chunk.metadata.get("chunk_id", "未知片段")

        st.markdown(f"### Chunk {i}")
        st.write(f"来源：{source}")
        st.write(f"类型：{file_type}")
        st.write(f"位置：{location}")
        st.write(f"Chunk 编号：{chunk_id}")
        st.write(chunk.page_content)


# =========================
# 向量库
# =========================

if st.button("建立向量库"):
    with st.spinner("正在向量化并建立向量库，请稍等..."):
        try:
            vector_db = create_vector_db(chunks)
            st.session_state["vector_db"] = vector_db
            st.success("向量库建立完成！")
        except Exception as e:
            st.error(f"向量库建立失败：{e}")

if st.session_state["vector_db"] is None:
    st.warning("请先点击“建立向量库”，再开始提问。")


# =========================
# 多轮问答
# =========================

st.divider()
st.subheader("多轮问答")

col1, col2 = st.columns([1, 5])

with col1:
        if st.button("清空对话"):
            st.session_state["chat_history"] = []
            st.session_state["last_log_row"] = None
            st.session_state["last_card_results"] = []
            st.session_state["last_card_source_info"] = {}
            st.session_state["last_card_saved"] = False
            st.session_state["editable_question_text"] = ""
            st.session_state["editable_math_items"] = []
            st.rerun()

with col2:
    st.write(
        "当前支持：数学题目解析、错题卡生成、错题库、PDF 错题集导出、LangGraph、RAG、Rerank、Memory、日志。"
    )


# 显示历史对话
for msg in st.session_state["chat_history"]:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            st.write(msg["content"])


question = st.chat_input("请输入你的问题")

if question:
    st.session_state["last_card_saved"] = False

    with st.chat_message("user"):
        st.write(question)

    with st.spinner("正在运行 LangGraph Agent 工作流..."):
        graph_result = run_agent_graph(
            question=question,
            chat_history=st.session_state.get("chat_history", []),
            vector_db=st.session_state.get("vector_db"),
            chunks=st.session_state.get("chunks", []),
        )

    task_info = graph_result.get("task_info", {})
    answer = graph_result.get("answer", "")
    retrieval_question = graph_result.get("retrieval_question", "")
    candidate_docs_with_scores = graph_result.get("candidate_docs_with_scores", [])
    retrieved_docs_with_scores = graph_result.get("retrieved_docs_with_scores", [])
    rerank_used = graph_result.get("rerank_used", False)
    validation_result = graph_result.get("validation_result", {})
    was_repaired = graph_result.get("was_repaired", False)
    elapsed_seconds = graph_result.get("elapsed_seconds", 0)
    graph_error = graph_result.get("error", "")
    top_k = graph_result.get("top_k", "")

    math_question_type = graph_result.get("math_question_type", "")

    if not math_question_type:
        math_question_type = graph_result.get("stat_question_type", "")

    math_items = graph_result.get("math_items", [])

    if not math_items:
        math_items = graph_result.get("stat_items", [])

    st.subheader("任务识别结果")
    st.json(task_info)

    if graph_result.get("route"):
        st.caption(f"LangGraph 路由结果：{graph_result.get('route')}")

    if math_question_type:
        st.caption(f"数学题型判断：{math_question_type}")

    if retrieval_question:
        st.subheader("实际检索问题")
        st.write(retrieval_question)

    if candidate_docs_with_scores:
        st.caption(
            f"Hybrid Retrieval 初筛候选数：{len(candidate_docs_with_scores)}；"
            f"Rerank 是否启用：{rerank_used}；"
            f"最终进入回答的片段数：{len(retrieved_docs_with_scores)}"
        )

    if retrieved_docs_with_scores:
        st.subheader("检索到的资料片段")

        for i, item in enumerate(retrieved_docs_with_scores, start=1):
            doc, score = item
            metadata = doc.metadata or {}

            with st.expander(f"资料片段 {i} | 综合分数：{score}"):
                st.write(f"来源文件：{metadata.get('source', '')}")
                st.write(f"文件类型：{metadata.get('file_type', '')}")
                st.write(f"位置：{metadata.get('location', '')}")

                if "chunk_id" in metadata:
                    st.write(f"Chunk ID：{metadata.get('chunk_id')}")

                if "_retrieval_method" in metadata:
                    st.write(f"检索方式：{metadata.get('_retrieval_method')}")

                if "_vector_distance" in metadata:
                    st.write(f"向量距离：{metadata.get('_vector_distance')}")

                if "_vector_similarity" in metadata:
                    st.write(f"向量相似度：{metadata.get('_vector_similarity')}")

                if "_rule_score" in metadata:
                    st.write(f"规则分数：{metadata.get('_rule_score')}")

                if "_rule_reasons" in metadata:
                    st.write(f"规则命中原因：{metadata.get('_rule_reasons')}")

                if "_rerank_used" in metadata:
                    st.write(f"是否经过 Rerank：{metadata.get('_rerank_used')}")

                if "_rerank_score" in metadata:
                    st.write(f"Rerank 分数：{metadata.get('_rerank_score')}")

                if "_rerank_reason" in metadata:
                    st.write(f"Rerank 理由：{metadata.get('_rerank_reason')}")

                if "_original_retrieval_score" in metadata:
                    st.write(f"原始检索分数：{metadata.get('_original_retrieval_score')}")

                if "_rerank_error" in metadata:
                    st.write(f"Rerank 错误：{metadata.get('_rerank_error')}")

                st.write("内容：")
                st.write(doc.page_content)

    if validation_result:
        st.subheader("结构化输出校验结果")
        st.json(validation_result)

    if was_repaired:
        st.info("系统已触发 Guardrails，并自动修复了一次答案格式。")

    if graph_error:
        st.warning(f"运行提示：{graph_error}")

    card_results = []

    with st.chat_message("assistant"):
        if math_items:
            render_math_exam_items(math_items)

            question_text_for_card = infer_question_text_for_card(
                user_question=question,
                retrieved_docs_with_scores=retrieved_docs_with_scores,
            )

            card_results = render_html_cards_for_items(
                question_text=question_text_for_card,
                items=math_items,
            )

            render_wrong_cards(card_results)

            # 保存当前可编辑版本
            st.session_state["editable_question_text"] = question_text_for_card
            st.session_state["editable_math_items"] = math_items

            # 保存当前图片结果
            st.session_state["last_card_results"] = card_results
            st.session_state["last_card_source_info"] = build_source_info(
                retrieved_docs_with_scores
            )
            st.session_state["last_card_saved"] = False

            # chat_history 里保存 JSON 文本，方便导出和 Memory
            assistant_history_content = answer

        else:
            st.write(answer)
            assistant_history_content = answer


    st.session_state["chat_history"].append(
        {
            "role": "user",
            "content": question,
        }
    )

    st.session_state["chat_history"].append(
        {
            "role": "assistant",
            "content": assistant_history_content,
        }
    )

    if ENABLE_SQLITE_MEMORY:
        try:
            memory_retrieved_sources = build_retrieved_sources(
                retrieved_docs_with_scores
            )

            save_qa_turn(
                session_id=st.session_state.get("session_id", ""),
                question=question,
                answer=assistant_history_content,
                file_key=st.session_state.get("current_file_key", ""),
                file_names=st.session_state.get("current_file_names", []),
                task_info=task_info,
                route=graph_result.get("route", ""),
                retrieval_question=retrieval_question,
                top_k=top_k,
                candidate_top_n=graph_result.get("candidate_top_n", ""),
                rerank_used=graph_result.get("rerank_used", False),
                retrieved_sources=memory_retrieved_sources,
                validation_result=validation_result,
                was_repaired=was_repaired,
                elapsed_seconds=elapsed_seconds,
                error=graph_error,
            )

        except Exception as e:
            st.warning(f"SQLite Memory 写入失败：{e}")

    try:
        log_row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": st.session_state.get("session_id", ""),
            "file_key": st.session_state.get("current_file_key", ""),
            "question": question,
            "task_type": task_info.get("task_type", ""),
            "need_rag": task_info.get("need_rag", ""),
            "answer_format": task_info.get("answer_format", ""),
            "task_reason": task_info.get("reason", ""),
            "retrieval_question": retrieval_question,
            "top_k": top_k,
            "retrieved_sources": build_retrieved_sources(retrieved_docs_with_scores),
            "answer_length": len(assistant_history_content),
            "format_valid": validation_result.get("valid", "") if isinstance(validation_result, dict) else "",
            "missing_fields": validation_result.get("missing_fields", []) if isinstance(validation_result, dict) else [],
            "was_repaired": 1 if was_repaired else 0,
            "elapsed_seconds": elapsed_seconds,
            "error": graph_error,
        }

        write_agent_log(log_row)
        st.session_state["last_log_row"] = log_row

    except Exception as e:
        st.warning(f"日志写入失败：{e}")

# =========================
# 持久化错题卡保存按钮
# =========================

if ENABLE_WRONGBOOK and st.session_state.get("last_card_results"):
    st.divider()
    st.subheader("保存错题卡")

    if st.session_state.get("last_card_saved", False):
        st.success("本轮错题卡已加入错题库。")
    else:
        st.info("当前已有生成的错题卡，可以加入错题库。")

        if st.button("加入错题库", key="save_last_cards_to_wrongbook"):
            try:
                saved_ids = save_wrong_question_cards(
                    session_id=st.session_state.get("session_id", ""),
                    card_results=st.session_state.get("last_card_results", []),
                    source_info=st.session_state.get("last_card_source_info", {}),
                )

                st.session_state["last_card_saved"] = True
                st.success(f"已加入错题库，共保存 {len(saved_ids)} 道题。")

                # 关键：保存后重新运行页面，让左侧错题库数量刷新
                st.rerun()

            except Exception as e:
                st.error(f"加入错题库失败：{e}")

render_card_edit_area()