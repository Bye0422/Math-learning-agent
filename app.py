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
    get_wrong_questions_filtered,
    get_wrongbook_review_summary,
    count_wrong_questions,
    export_wrong_questions_to_pdf,
    export_wrong_questions_to_pdf_by_ids,
    update_wrong_question_review,
)

from services.card_edit_service import (
    build_item_from_user_edit,
    edit_card_with_llm,
)
from state.session_state import (
    init_session_state,
    reset_chat_state,
    reset_document_state,
    start_new_file_session,
)
from ui.chunk_debug_panel import render_chunk_debug_panel
from ui.result_views import (
    render_math_exam_items,
    render_pdf_quality_result,
    render_wrong_cards,
)
from ui.theme import (
    close_chat_stage,
    render_app_header,
    render_global_styles,
    render_section_note,
    render_sidebar_brand,
    render_status_grid,
    open_chat_stage,
)

# =========================
# 页面设置
# =========================

st.set_page_config(page_title=APP_PAGE_TITLE, layout="wide")
render_global_styles()


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

init_session_state()
render_app_header(APP_TITLE)


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
    render_sidebar_brand(
        PRODUCT_NAME,
        PRODUCT_CHINESE_NAME,
        st.session_state["session_id"],
    )
    st.subheader("运行信息")
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

        review_summary = get_wrongbook_review_summary(
            due_before=datetime.now().strftime("%Y-%m-%d")
        )
        status_labels = {
            "new": "新错题",
            "reviewing": "复习中",
            "mastered": "已掌握",
        }
        status_counts = review_summary.get("by_status", {})

        st.write(f"待复习错题：{review_summary.get('due_count', 0)}")
        st.write(f"累计复习次数：{review_summary.get('total_review_count', 0)}")

        with st.expander("复习状态概览"):
            for status_key, label in status_labels.items():
                st.write(f"{label}：{status_counts.get(status_key, 0)}")

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

        with st.expander("筛选与批量导出"):
            filter_keyword = st.text_input(
                "搜索题干、解析或标签",
                key="wrongbook_filter_keyword",
            )
            filter_type = st.selectbox(
                "题型",
                options=["全部", "选择题", "判断题", "简答题", "填空题", "计算题"],
                key="wrongbook_filter_type",
            )
            filter_difficulty = st.selectbox(
                "难度",
                options=["全部", 1, 2, 3, 4, 5],
                key="wrongbook_filter_difficulty",
            )
            filter_tag = st.text_input(
                "标签精确匹配",
                key="wrongbook_filter_tag",
            )
            filter_review_status = st.selectbox(
                "复习状态",
                options=["全部", "new", "reviewing", "mastered"],
                format_func=lambda value: {
                    "全部": "全部",
                    "new": "新错题",
                    "reviewing": "复习中",
                    "mastered": "已掌握",
                }.get(value, value),
                key="wrongbook_filter_review_status",
            )
            filter_due_only = st.checkbox(
                "只看今天前到期",
                key="wrongbook_filter_due_only",
            )

            filtered_wrong_questions = get_wrong_questions_filtered(
                question_type="" if filter_type == "全部" else filter_type,
                difficulty=None if filter_difficulty == "全部" else filter_difficulty,
                tag=filter_tag,
                keyword=filter_keyword,
                review_status="" if filter_review_status == "全部" else filter_review_status,
                due_before=datetime.now().strftime("%Y-%m-%d") if filter_due_only else None,
                limit=200,
            )

            st.write(f"匹配错题数：{len(filtered_wrong_questions)}")

            option_to_id = {}
            options = []

            for wrong in filtered_wrong_questions[:50]:
                tags = " / ".join(wrong.get("tags", []))
                question_text = wrong.get("question_text", "").replace("\n", " ")
                label = (
                    f"{wrong.get('type', '')} | 难度 {wrong.get('difficulty', '')} | "
                    f"{status_labels.get(wrong.get('review_status', 'new'), wrong.get('review_status', 'new'))} | "
                    f"{tags} | {question_text[:28]}"
                )
                option_to_id[label] = wrong.get("id", "")
                options.append(label)

            selected_labels = st.multiselect(
                "选择要导出的错题",
                options=options,
                key="wrongbook_selected_export_labels",
            )

            selected_ids = [
                option_to_id[label]
                for label in selected_labels
                if option_to_id.get(label)
            ]

            if st.button("导出选中错题 PDF", key="export_selected_wrongbook_pdf"):
                if not selected_ids:
                    st.warning("请先选择至少一道错题。")
                else:
                    try:
                        pdf_path = export_wrong_questions_to_pdf_by_ids(selected_ids)

                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="下载选中错题 PDF",
                                data=f.read(),
                                file_name="wrongbook_selected.pdf",
                                mime="application/pdf",
                            )

                        st.success(f"已生成选中错题 PDF，共 {len(selected_ids)} 道题。")

                    except Exception as e:
                        st.error(f"导出选中错题失败：{e}")

            st.write("---")
            st.write("复习记录")

            review_options = options[:]
            selected_review_label = st.selectbox(
                "选择要更新的错题",
                options=[""] + review_options,
                format_func=lambda value: "请选择错题" if value == "" else value,
                key="wrongbook_review_selected_label",
            )

            if selected_review_label:
                selected_review_id = option_to_id.get(selected_review_label)
                selected_wrong = next(
                    (
                        item
                        for item in filtered_wrong_questions
                        if item.get("id") == selected_review_id
                    ),
                    {},
                )

                review_status_value = st.selectbox(
                    "更新复习状态",
                    options=["new", "reviewing", "mastered"],
                    index=["new", "reviewing", "mastered"].index(
                        selected_wrong.get("review_status", "new")
                        if selected_wrong.get("review_status", "new") in ["new", "reviewing", "mastered"]
                        else "new"
                    ),
                    format_func=lambda value: status_labels.get(value, value),
                    key="wrongbook_review_status_update",
                )
                mistake_reason_value = st.text_area(
                    "错因记录",
                    value=selected_wrong.get("mistake_reason", ""),
                    key="wrongbook_mistake_reason_update",
                )
                next_review_date = st.date_input(
                    "下次复习日期",
                    key="wrongbook_next_review_date_update",
                )
                mark_reviewed = st.checkbox(
                    "本次已完成复习",
                    key="wrongbook_mark_reviewed",
                )

                if st.button("保存复习记录", key="save_wrongbook_review"):
                    updated = update_wrong_question_review(
                        selected_review_id,
                        mistake_reason=mistake_reason_value,
                        review_status=review_status_value,
                        next_review_at=next_review_date.strftime("%Y-%m-%d"),
                        last_reviewed_at=(
                            datetime.now().strftime("%Y-%m-%d")
                            if mark_reviewed
                            else None
                        ),
                    )

                    if updated:
                        st.success("复习记录已保存。")
                        st.rerun()
                    else:
                        st.warning("没有可保存的复习记录。")

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

render_status_grid(
    [
        {
            "label": "当前文档",
            "value": len(st.session_state.get("current_file_names", [])),
            "note": "已载入文件数",
        },
        {
            "label": "原始 Document",
            "value": len(st.session_state.get("documents", [])),
            "note": "解析后的文档单元",
        },
        {
            "label": "Chunk",
            "value": len(st.session_state.get("chunks", [])),
            "note": "进入检索的文本块",
        },
        {
            "label": "向量库",
            "value": "就绪" if st.session_state.get("vector_db") is not None else "未就绪",
            "note": "文档问答依赖此状态",
        },
    ]
)

st.subheader("资料辅助区")
render_section_note("资料上传、解析和 Chunk 调试作为对话的上下文支持；主要学习操作集中在下方 AI 对话区。")

uploaded_files = st.file_uploader(
    "上传文档",
    type=SUPPORTED_FILE_TYPES,
    accept_multiple_files=True,
)

has_uploaded_files = bool(uploaded_files)

if has_uploaded_files:
    current_file_names = [file.name for file in uploaded_files]
    current_file_key = "|".join(
        [f"{file.name}_{file.size}" for file in uploaded_files]
    )
else:
    current_file_names = []
    current_file_key = ""

if not has_uploaded_files and st.session_state["current_file_key"]:
    reset_document_state()

# 换文件后，清空旧状态
if has_uploaded_files and st.session_state["current_file_key"] != current_file_key:
    start_new_file_session(current_file_key, current_file_names)


# =========================
# 文档解析
# =========================

if not has_uploaded_files:
    st.info("可以先上传 PDF、Word、TXT 或图片文件后进行文档问答；也可以直接提问使用计算器、日志查询或闲聊能力。")

if has_uploaded_files and not st.session_state["documents"]:
    with st.spinner("正在解析上传文件..."):
        documents, load_errors = read_multiple_files_to_documents(uploaded_files)

    st.session_state["documents"] = documents

    for error in load_errors:
        st.warning(error)

documents = st.session_state["documents"]

if has_uploaded_files and not documents:
    st.warning("没有成功读取到文档内容，请检查文件格式或重新上传。")

if documents:
    render_pdf_quality_result(documents)

    full_text = "\n\n".join([doc.page_content for doc in documents])

    with st.expander("文档读取详情", expanded=False):
        render_section_note("这里展示解析后的前 1000 个字符，用于快速确认资料是否读取正确。")
        st.write(full_text[:1000])

        st.success(
            f"读取完成，共读取 {len(uploaded_files)} 个文件，"
            f"共生成 {len(documents)} 个原始 Document，"
            f"共 {len(full_text)} 个字符。"
        )

        st.write("已上传文件")
        for file_name in current_file_names:
            st.write(f"- {file_name}")


# =========================
# Chunk 切分
# =========================

if documents and not st.session_state["chunks"]:
    chunks = split_documents(documents)
    st.session_state["chunks"] = chunks

chunks = st.session_state["chunks"]

if chunks:
    st.subheader("资料质量与 Chunk")
    render_section_note("Chunk 是进入 RAG 检索的最小上下文单元。优先检查高风险 chunk，再进行问答。")
    st.success(f"共切分出 {len(chunks)} 个 chunk。")
    render_chunk_debug_panel(chunks)


# =========================
# 向量库
# =========================

if chunks and st.session_state["vector_db"] is None and not st.session_state["vector_build_error"]:
    with st.spinner("正在自动向量化并建立向量库，请稍等..."):
        try:
            vector_db = create_vector_db(chunks)
            st.session_state["vector_db"] = vector_db
            st.session_state["vector_build_file_key"] = st.session_state.get("current_file_key", "")
            st.success("向量库已自动建立，可以开始提问。")
        except Exception as e:
            st.session_state["vector_build_error"] = str(e)
            st.error(f"向量库自动建立失败：{e}")

if chunks and st.session_state["vector_db"] is not None:
    st.success("向量库状态：已就绪。")

if chunks and st.session_state["vector_build_error"]:
    st.warning("向量库状态：自动建立失败，可以检查 API 配置或网络后手动重试。")

if chunks and st.button("重新建立向量库"):
    with st.spinner("正在向量化并建立向量库，请稍等..."):
        try:
            vector_db = create_vector_db(chunks)
            st.session_state["vector_db"] = vector_db
            st.session_state["vector_build_error"] = ""
            st.session_state["vector_build_file_key"] = st.session_state.get("current_file_key", "")
            st.success("向量库建立完成！")
        except Exception as e:
            st.session_state["vector_build_error"] = str(e)
            st.error(f"向量库建立失败：{e}")

if has_uploaded_files and chunks and st.session_state["vector_db"] is None:
    st.warning("当前文档尚未完成向量库构建，文档问答暂不可用；工具类问题仍可提问。")


# =========================
# 多轮问答
# =========================

st.divider()
open_chat_stage()
st.subheader("AI 对话主工作区")
render_section_note("这是页面的主要操作区。你可以直接提问、让系统讲题、生成错题卡，或查询运行日志。")

col1, col2 = st.columns([1, 5])

with col1:
        if st.button("清空对话"):
            reset_chat_state()
            st.rerun()

with col2:
    st.write(
        "当前支持：无文档工具问答、文档自动建库、数学题目解析、错题卡生成、错题库、PDF 错题集导出、LangGraph、RAG、Rerank、Memory、日志。"
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

                if "_retrieval_explanation" in metadata:
                    st.write("结构化检索解释：")
                    st.json(metadata.get("_retrieval_explanation"))

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

close_chat_stage()

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
