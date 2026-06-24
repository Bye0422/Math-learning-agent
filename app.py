from datetime import datetime
from html import escape
import importlib
import json
from pathlib import Path
import re

import streamlit as st

from config import (
    APP_PAGE_TITLE,
    SUPPORTED_FILE_TYPES,
    EXPORT_FILE_PREFIX,
    ENABLE_SQLITE_MEMORY,
    MEMORY_HISTORY_LIMIT,
    PRODUCT_NAME,
    PRODUCT_CHINESE_NAME,
    ENABLE_WRONGBOOK,
)
from services.agent_graph import run_agent_graph
from services.card_edit_service import build_item_from_user_edit
from services.card_html_render_service import render_html_cards_for_items
from services.card_render_service import infer_question_text_for_card, build_source_info
from services.document_loader import read_multiple_files_to_documents
from services.export_service import build_export_text, build_export_docx_bytes
from services.llm_service import check_env
from services.log_service import (
    LOG_FILE,
    build_retrieved_sources,
    ensure_log_file,
    write_agent_log,
)
from services.memory_service import (
    clear_session_memory,
    get_recent_sessions,
    init_memory_db,
    load_chat_history,
    save_qa_turn,
)
from services.vector_service import create_vector_db, split_documents
from services.wrongbook_service import (
    count_wrong_questions,
    export_wrong_questions_to_pdf_by_ids,
    get_wrong_questions_filtered,
    get_wrongbook_review_summary,
    init_wrongbook_db,
    save_wrong_question_cards,
)
from state.session_state import (
    init_session_state,
    reset_card_state,
    reset_chat_state,
    start_new_file_session,
)
from ui.chunk_debug_panel import render_chunk_debug_panel
from ui.result_views import render_wrong_cards
import ui.theme as theme


st.set_page_config(page_title=APP_PAGE_TITLE, layout="wide")
theme = importlib.reload(theme)
theme.render_global_styles()
init_session_state()

try:
    check_env()
    ensure_log_file()
    if ENABLE_SQLITE_MEMORY:
        init_memory_db()
    if ENABLE_WRONGBOOK:
        init_wrongbook_db()
except Exception as exc:
    st.error(str(exc))
    st.stop()

if ENABLE_SQLITE_MEMORY and not st.session_state["memory_loaded"]:
    loaded_history = load_chat_history(
        session_id=st.session_state["session_id"],
        limit=MEMORY_HISTORY_LIMIT,
    )
    if loaded_history:
        st.session_state["chat_history"] = loaded_history
    st.session_state["memory_loaded"] = True


PAGE_LABELS = {
    "workspace": ("陪伴对话", "可以聊天、整理情绪，也可以继续学习"),
    "chat": ("陪伴对话", "基于资料回答问题，需要时再制作错题卡"),
    "chunks": ("资料校正", "检查并修正资料识别片段"),
}

TYPE_OPTIONS = ["选择题", "判断题", "简答题", "填空题", "计算题"]
WRONGBOOK_FILTER_DEFAULTS = {
    "drawer_wrongbook_keyword": "",
    "drawer_wrongbook_type": "全部",
    "drawer_wrongbook_difficulty": "全部",
    "drawer_wrongbook_tag": "",
    "drawer_wrongbook_review_status": "全部",
    "drawer_wrongbook_due_only": False,
}

DAILY_TASK_TARGET = 10
DAILY_PROGRESS_FILE = Path("data/daily_learning_progress.json")


def save_daily_task_progress(completed):
    completed = max(0, min(DAILY_TASK_TARGET, int(completed)))
    DAILY_PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DAILY_PROGRESS_FILE.write_text(
        json.dumps(
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "completed": completed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def get_daily_task_progress():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        payload = json.loads(DAILY_PROGRESS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        save_daily_task_progress(0)
        return 0

    if payload.get("date") != today:
        save_daily_task_progress(0)
        return 0

    try:
        completed = int(payload.get("completed", 0))
    except (TypeError, ValueError):
        completed = 0
    return max(0, min(DAILY_TASK_TARGET, completed))


def increment_daily_task_progress():
    completed = min(DAILY_TASK_TARGET, get_daily_task_progress() + 1)
    save_daily_task_progress(completed)
    return completed


def clean_text(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def truncate_text(value, max_length=90):
    text = clean_text(value)
    return text if len(text) <= max_length else text[:max_length] + "..."


def close_drawers():
    st.session_state["materials_drawer_open"] = False
    st.session_state["history_drawer_open"] = False
    st.session_state["wrongbook_drawer_open"] = False


def navigate(page):
    st.session_state["active_page"] = page
    close_drawers()


def reset_wrongbook_filters():
    for key, value in WRONGBOOK_FILTER_DEFAULTS.items():
        st.session_state[key] = value


def safe_wrongbook_summary():
    if not ENABLE_WRONGBOOK:
        return {"total": 0, "due_count": 0, "reviewing": 0}
    try:
        total = count_wrong_questions()
    except Exception:
        total = 0
    try:
        summary = get_wrongbook_review_summary(
            due_before=datetime.now().strftime("%Y-%m-%d")
        )
    except Exception:
        summary = {}
    by_status = summary.get("by_status", {}) if isinstance(summary, dict) else {}
    return {
        "total": total,
        "due_count": summary.get("due_count", 0) if isinstance(summary, dict) else 0,
        "reviewing": by_status.get("reviewing", 0),
    }


def build_export_payloads():
    chat_history = st.session_state.get("chat_history", [])
    if not chat_history:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_text = build_export_text(
        chat_history=chat_history,
        file_names=st.session_state.get("current_file_names", []),
        session_id=st.session_state.get("session_id", ""),
        last_log_row=st.session_state.get("last_log_row"),
    )
    export_docx = build_export_docx_bytes(
        chat_history=chat_history,
        file_names=st.session_state.get("current_file_names", []),
        session_id=st.session_state.get("session_id", ""),
        last_log_row=st.session_state.get("last_log_row"),
    )
    return export_text, export_docx, timestamp


def build_pdf_download_payload(pdf_path):
    path = Path(pdf_path)
    return path.read_bytes(), path.name


def render_left_navigation():
    active_page = st.session_state.get("active_page", "workspace")
    with st.container(key="mla_left_navigation"):
        st.markdown(
            f"""
            <div class="mla-nav-brand">
                <div class="mla-nav-logo" aria-hidden="true">
                    <span>M</span>
                    <i></i>
                </div>
                <div class="mla-nav-brand-copy">
                    <strong>{escape(str(PRODUCT_NAME))}</strong>
                    <span>{escape(str(PRODUCT_CHINESE_NAME))}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "✦  对话",
            key="nav_workspace",
            type="primary" if active_page == "workspace" else "secondary",
            use_container_width=True,
        ):
            navigate("workspace")
            st.rerun()

        if st.button("+  资料", key="nav_materials", use_container_width=True):
            st.session_state["materials_drawer_open"] = True
            st.session_state["history_drawer_open"] = False
            st.session_state["wrongbook_drawer_open"] = False
            st.rerun()

        if st.button(
            "✎  资料校正",
            key="nav_chunks",
            type="primary" if active_page == "chunks" else "secondary",
            use_container_width=True,
        ):
            navigate("chunks")
            st.rerun()
        if st.button("▤  错题库", key="nav_wrongbook", use_container_width=True):
            st.session_state["wrongbook_drawer_open"] = True
            st.session_state["materials_drawer_open"] = False
            st.session_state["history_drawer_open"] = False
            st.rerun()
        if st.button("◷  历史记录", key="nav_history", use_container_width=True):
            st.session_state["history_drawer_open"] = True
            st.session_state["materials_drawer_open"] = False
            st.session_state["wrongbook_drawer_open"] = False
            st.rerun()

        stats = safe_wrongbook_summary()
        done = get_daily_task_progress()
        progress_percent = int(done / DAILY_TASK_TARGET * 100)
        st.markdown(
            f"""
            <div class="mla-daily-goal">
                <strong>今日学习</strong>
                <span>已完成 {done} / {DAILY_TASK_TARGET} 个任务</span>
                <div class="mla-goal-track"><div class="mla-goal-value" style="width:{progress_percent}%"></div></div>
                <small>错题 {stats["total"]} · 到期 {stats["due_count"]}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_topbar():
    title, subtitle = PAGE_LABELS.get(
        st.session_state.get("active_page", "workspace"), PAGE_LABELS["workspace"]
    )
    with st.container(key="mla_topbar"):
        st.markdown(
            f"""
            <div class="mla-topbar-inner">
                <div class="mla-top-title">
                    <strong>{escape(title)}</strong>
                    <span>{escape(subtitle)}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def processing_modal_html(file_name, file_size, progress, stage):
    stage_order = ["读取文档", "识别结构", "生成 Chunk", "建立向量索引"]
    labels = {
        "读取文档": "文档读取",
        "识别结构": "页面结构识别",
        "生成 Chunk": "生成题目片段",
        "建立向量索引": "建立索引",
    }
    current_index = stage_order.index(stage) if stage in stage_order else 0
    suffix = str(file_name).rsplit(".", 1)[-1].upper() if "." in str(file_name) else "文件"
    suffix = suffix if len(suffix) <= 5 else "文件"
    rows = []
    for index, item in enumerate(stage_order):
        label = labels[item]
        if index < current_index:
            rows.append(f'<span class="done">✓ {escape(label)}完成</span>')
        elif index == current_index:
            rows.append(f'<span class="active">• 正在{escape(label)}</span>')
        else:
            rows.append(f'<span class="pending">○ 等待{escape(label)}</span>')
    return f"""
    <section class="mla-processing-modal" role="status" aria-live="polite">
        <h3>正在解析学习资料</h3>
        <p>系统正在提取题目、公式和选项，并生成可检索的片段。</p>
        <div class="mla-processing-file">
            <span class="mla-file-type">{escape(suffix)}</span>
            <div><strong>{escape(file_name)}</strong><span>{escape(file_size)}</span></div>
        </div>
        <div class="mla-processing-track"><div class="mla-processing-value" style="width:{max(4, min(100, progress))}%"></div></div>
        <div class="mla-processing-label">{progress}% · 正在{escape(labels.get(stage, stage))}</div>
        <div class="mla-processing-steps">{''.join(rows)}</div>
    </section>
    """


def update_processing_modal(placeholder, uploaded_files, progress, stage):
    first_file = uploaded_files[0]
    size_mb = getattr(first_file, "size", 0) / (1024 * 1024)
    file_size = f"{size_mb:.1f} MB · 共 {len(uploaded_files)} 个文件"
    placeholder.markdown(
        processing_modal_html(first_file.name, file_size, progress, stage),
        unsafe_allow_html=True,
    )


def process_uploaded_files(uploaded_files):
    if not uploaded_files:
        return

    current_file_names = [file.name for file in uploaded_files]
    current_file_key = "|".join(
        f"{file.name}_{getattr(file, 'size', 0)}" for file in uploaded_files
    )
    if st.session_state.get("current_file_key") != current_file_key:
        start_new_file_session(current_file_key, current_file_names)
    if st.session_state.get("upload_process_attempted_key") == current_file_key:
        return

    st.session_state["upload_process_attempted_key"] = current_file_key
    modal = st.empty()
    try:
        update_processing_modal(modal, uploaded_files, 12, "读取文档")
        documents, load_errors = read_multiple_files_to_documents(uploaded_files)
        st.session_state["documents"] = documents
        for error in load_errors:
            st.warning(error)

        update_processing_modal(modal, uploaded_files, 38, "识别结构")
        if not documents:
            raise ValueError("没有读取到可用内容，请检查文件格式或重新上传。")

        update_processing_modal(modal, uploaded_files, 66, "生成 Chunk")
        chunks = split_documents(documents)
        st.session_state["chunks"] = chunks
        if not chunks:
            raise ValueError("资料读取成功，但没有生成可用片段。")

        update_processing_modal(modal, uploaded_files, 84, "建立向量索引")
        vector_db = create_vector_db(chunks)
        st.session_state["vector_db"] = vector_db
        st.session_state["vector_build_file_key"] = current_file_key
        st.session_state["vector_build_error"] = ""
        update_processing_modal(modal, uploaded_files, 100, "建立向量索引")
        st.toast(f"已载入 {len(current_file_names)} 个文件，共 {len(chunks)} 个片段。")
    except Exception as exc:
        st.session_state["vector_build_error"] = str(exc)
        st.error(f"资料处理失败：{exc}")
    finally:
        modal.empty()


def render_upload_card(uploader_key="workspace_uploader"):
    with st.container(key="mla_upload_card"):
        st.markdown(
            """
            <div class="mla-card-header mla-upload-header">
                <div class="mla-card-icon upload">↥</div>
                <div class="mla-card-title big">
                    <strong>上传试卷、讲义或题目图片</strong>
                    <span>支持 PDF、Word、TXT 和图片；上传后可直接提问或校正识别片段。</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded_files = st.file_uploader(
            "选择文件",
            type=SUPPORTED_FILE_TYPES,
            accept_multiple_files=True,
            label_visibility="collapsed",
            key=uploader_key,
        )
        process_uploaded_files(uploaded_files)
        if st.session_state.get("vector_build_error"):
            st.caption(st.session_state["vector_build_error"])


def process_question(question):
    question = str(question or "").strip()
    if not question:
        return

    reset_card_state()
    with st.spinner("正在思考哦..."):
        graph_result = run_agent_graph(
            question=question,
            chat_history=st.session_state.get("chat_history", []),
            vector_db=st.session_state.get("vector_db"),
            chunks=st.session_state.get("chunks", []),
        )

    task_info = graph_result.get("task_info", {})
    answer = graph_result.get("answer", "")
    retrieved_docs_with_scores = graph_result.get("retrieved_docs_with_scores", [])
    validation_result = graph_result.get("validation_result", {})
    was_repaired = graph_result.get("was_repaired", False)
    graph_error = graph_result.get("error", "")
    math_items = graph_result.get("math_items", []) or graph_result.get("stat_items", [])

    if graph_error and not answer:
        answer = "这次解析遇到问题，请换一种问法再试。"

    if math_items:
        st.session_state["pending_card_question_text"] = infer_question_text_for_card(
            user_question=question,
            retrieved_docs_with_scores=retrieved_docs_with_scores,
        )
        st.session_state["pending_card_items"] = math_items
        st.session_state["pending_card_source_info"] = build_source_info(
            retrieved_docs_with_scores
        )

    st.session_state["chat_history"].extend(
        [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
    )

    if ENABLE_SQLITE_MEMORY:
        try:
            save_qa_turn(
                session_id=st.session_state.get("session_id", ""),
                question=question,
                answer=answer,
                file_key=st.session_state.get("current_file_key", ""),
                file_names=st.session_state.get("current_file_names", []),
                task_info=task_info,
                route=graph_result.get("route", ""),
                retrieval_question=graph_result.get("retrieval_question", ""),
                top_k=graph_result.get("top_k", ""),
                candidate_top_n=graph_result.get("candidate_top_n", ""),
                rerank_used=graph_result.get("rerank_used", False),
                retrieved_sources=build_retrieved_sources(retrieved_docs_with_scores),
                validation_result=validation_result,
                was_repaired=was_repaired,
                elapsed_seconds=graph_result.get("elapsed_seconds", 0),
                error=graph_error,
            )
        except Exception:
            pass

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
            "retrieval_question": graph_result.get("retrieval_question", ""),
            "top_k": graph_result.get("top_k", ""),
            "retrieved_sources": build_retrieved_sources(retrieved_docs_with_scores),
            "answer_length": len(answer),
            "format_valid": validation_result.get("valid", "")
            if isinstance(validation_result, dict)
            else "",
            "missing_fields": validation_result.get("missing_fields", [])
            if isinstance(validation_result, dict)
            else [],
            "was_repaired": 1 if was_repaired else 0,
            "elapsed_seconds": graph_result.get("elapsed_seconds", 0),
            "error": graph_error,
        }
        write_agent_log(log_row)
        st.session_state["last_log_row"] = log_row
    except Exception:
        pass

    st.rerun()


def render_chat_card():
    has_materials = bool(st.session_state.get("current_file_names"))
    source_label = "资料已连接" if has_materials else "可直接聊天"
    with st.container(key="mla_chat_card"):
        st.markdown(
            f"""
            <div class="mla-chat-head">
                <div class="mla-card-header">
                    <div class="mla-card-icon">✦</div>
                    <div class="mla-card-title">
                        <strong>陪伴式学习助手</strong>
                        <span>聊天、天气、情绪梳理和题目解析都从这里开始</span>
                    </div>
                </div>
                <span class="mla-source-pill">{escape(source_label)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        chat_history = st.session_state.get("chat_history", [])
        if not chat_history:
            st.markdown(
                """
                <div class="mla-chat-welcome">
                    <strong>你可以直接和我聊，也可以把学习问题发给我。</strong>
                    <span>“今天有点焦虑，陪我梳理一下。”</span>
                    <span>“这道题第一步怎么做？”</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for index, message in enumerate(chat_history[-12:]):
                role = message.get("role", "assistant")
                key = f"mla_chat_{'user' if role == 'user' else 'assistant'}_{index}"
                with st.container(key=key):
                    st.markdown(str(message.get("content", "")))

        with st.container(key="mla_chat_composer"):
            with st.form("chat_composer_form", clear_on_submit=True, border=False):
                input_col, button_col = st.columns([12, 1])
                with input_col:
                    question = st.text_input(
                        "问题",
                        placeholder="直接聊天、说说心情，或提一道题...",
                        label_visibility="collapsed",
                    )
                with button_col:
                    submitted = st.form_submit_button("↑", use_container_width=True)
            if submitted:
                process_question(question)


def render_card_edit_area():
    editable_items = st.session_state.get("editable_math_items", [])
    editable_question_text = st.session_state.get("editable_question_text", "")
    if not editable_items:
        return

    current_item = editable_items[0]
    with st.container(key="mla_card_editor_form"):
        st.markdown("### 确认题目内容")
        st.caption("保存到错题库前，可以修改题干、解析、难度和标签。")
        with st.form("manual_edit_card_form"):
            edited_question_text = st.text_area("题目", value=editable_question_text, height=150)
            edited_analysis = st.text_area(
                "解析", value=current_item.get("analysis", ""), height=170
            )
            col1, col2 = st.columns(2)
            with col1:
                edited_difficulty = st.select_slider(
                    "难度修改",
                    options=[1, 2, 3, 4, 5],
                    value=max(1, min(5, int(current_item.get("difficulty", 2)))),
                )
            with col2:
                current_type = current_item.get("type", "计算题")
                edited_type = st.selectbox(
                    "题型",
                    options=TYPE_OPTIONS,
                    index=TYPE_OPTIONS.index(current_type)
                    if current_type in TYPE_OPTIONS
                    else TYPE_OPTIONS.index("计算题"),
                )
            edited_tags_text = st.text_input(
                "标签修改",
                value=", ".join(current_item.get("tags", [])),
                placeholder="例如：导数 函数单调性 易错",
            )
            submitted = st.form_submit_button("更新错题卡", type="primary")

        if submitted:
            if not edited_question_text.strip() or not edited_analysis.strip():
                st.error("题目和解析不能为空。")
            else:
                try:
                    new_item = build_item_from_user_edit(
                        analysis=edited_analysis,
                        difficulty=edited_difficulty,
                        question_type=edited_type,
                        tags_text=edited_tags_text,
                    )
                    new_results = render_html_cards_for_items(
                        question_text=edited_question_text,
                        items=[new_item],
                    )
                    st.session_state["editable_question_text"] = edited_question_text
                    st.session_state["editable_math_items"] = [new_item]
                    st.session_state["last_card_results"] = new_results
                    st.session_state["last_card_saved"] = False
                    st.success("错题卡已更新。")
                    st.rerun()
                except Exception as exc:
                    st.error(f"更新错题卡失败：{exc}")

        if st.session_state.get("last_card_results"):
            render_wrong_cards(st.session_state["last_card_results"])


def render_pending_card_flow():
    if not ENABLE_WRONGBOOK:
        return

    pending_items = st.session_state.get("pending_card_items", [])
    card_results = st.session_state.get("last_card_results", [])
    if pending_items and not card_results:
        with st.container(key="mla_card_editor_generate"):
            st.markdown("### 生成错题卡")
            st.caption("解析确认后再生成卡片，之后可以继续修改题目、难度和标签。")
            if st.button("生成错题卡", key="generate_wrong_card_from_answer", type="primary"):
                try:
                    new_results = render_html_cards_for_items(
                        question_text=st.session_state.get("pending_card_question_text", ""),
                        items=pending_items,
                    )
                    st.session_state["editable_question_text"] = st.session_state.get(
                        "pending_card_question_text", ""
                    )
                    st.session_state["editable_math_items"] = pending_items
                    st.session_state["last_card_results"] = new_results
                    st.session_state["last_card_source_info"] = st.session_state.get(
                        "pending_card_source_info", {}
                    )
                    st.session_state["last_card_saved"] = False
                    st.rerun()
                except Exception as exc:
                    st.error(f"生成错题卡失败：{exc}")

    render_card_edit_area()

    if st.session_state.get("last_card_results"):
        with st.container(key="mla_card_editor_save"):
            if st.session_state.get("last_card_saved", False):
                st.success("这张错题卡已导入错题库。")
            elif st.button("导入错题库", key="save_last_cards_to_wrongbook", type="primary"):
                try:
                    saved_ids = save_wrong_question_cards(
                        session_id=st.session_state.get("session_id", ""),
                        card_results=st.session_state.get("last_card_results", []),
                        source_info=st.session_state.get("last_card_source_info", {}),
                    )
                    if saved_ids:
                        increment_daily_task_progress()
                    st.session_state["last_card_saved"] = True
                    st.success(f"已导入 {len(saved_ids)} 张错题卡。")
                    st.rerun()
                except Exception as exc:
                    st.error(f"导入错题库失败：{exc}")


def render_today_plan():
    has_chat = bool(st.session_state.get("chat_history"))
    has_materials = bool(st.session_state.get("current_file_names"))
    with st.container(key="mla_today_plan"):
        st.markdown('<div class="mla-card-kicker">今天可以聊</div>', unsafe_allow_html=True)
        st.caption("先把当前感受或问题说出来，必要时再接入资料")
        rows = [
            ("done" if has_chat else "active", "日常聊天", "已开始" if has_chat else "可直接开始"),
            ("done" if has_materials else "", "结合资料答疑", "资料已接入" if has_materials else "按需上传"),
            ("", "整理错题", "需要时生成"),
        ]
        for status, title, note in rows:
            st.markdown(
                f"""
                <div class="mla-plan-row">
                    <span class="mla-plan-dot {escape(status)}"></span>
                    <div class="mla-plan-copy"><strong>{escape(title)}</strong><span>{escape(note)}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_sources_card():
    file_names = st.session_state.get("current_file_names", [])
    chunks = st.session_state.get("chunks", [])
    with st.container(key="mla_sources_card"):
        st.markdown('<div class="mla-card-kicker">当前资料</div>', unsafe_allow_html=True)
        if not file_names:
            st.markdown(
                '<div class="mla-empty-note">还没有上传资料，可以直接向 AI 提问。</div>',
                unsafe_allow_html=True,
            )
        else:
            per_file_chunks = max(1, len(chunks) // max(1, len(file_names)))
            for file_name in file_names[:2]:
                st.markdown(
                    f"""
                    <div class="mla-source-row">
                        <span class="mla-source-icon">文</span>
                        <div class="mla-source-copy">
                            <strong>{escape(str(file_name))}</strong>
                            <span>{per_file_chunks} 个片段</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        if st.button("打开资料栏", key="manage_sources"):
            st.session_state["materials_drawer_open"] = True
            st.session_state["history_drawer_open"] = False
            st.session_state["wrongbook_drawer_open"] = False
            st.rerun()


def render_review_card():
    stats = safe_wrongbook_summary()
    with st.container(key="mla_review_card"):
        st.markdown('<div class="mla-card-kicker">错题复习</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("全部", stats["total"])
        c2.metric("到期", stats["due_count"])
        c3.metric("复习中", stats["reviewing"])
        if st.button("进入错题库", key="open_wrongbook_from_rail"):
            st.session_state["wrongbook_drawer_open"] = True
            st.session_state["materials_drawer_open"] = False
            st.session_state["history_drawer_open"] = False
            st.rerun()


def render_study_tip():
    with st.container(key="mla_study_tip"):
        st.markdown('<div class="mla-card-kicker">陪伴提示</div>', unsafe_allow_html=True)
        st.markdown("**如果只是想聊一会儿，可以直接输入当前心情；如果要学习，再把题目或资料交给我。**")
        st.caption("建议：先说目标，再让 AI 帮你拆成下一步")


def render_right_rail():
    render_today_plan()
    render_sources_card()
    render_review_card()
    render_study_tip()


def render_history_drawer():
    if not st.session_state.get("history_drawer_open"):
        return

    st.markdown('<div class="mla-drawer-scrim"></div>', unsafe_allow_html=True)
    with st.container(key="mla_history_drawer"):
        title_col, close_col = st.columns([5, 1])
        with title_col:
            st.markdown(
                """
                <div class="mla-drawer-title">
                    <strong>历史对话</strong>
                    <span>悬浮抽屉 · 不离开当前学习上下文</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with close_col:
            if st.button("关闭", key="close_history_drawer"):
                st.session_state["history_drawer_open"] = False
                st.rerun()

        keyword = st.text_input(
            "搜索历史",
            placeholder="输入题目关键词...",
            key="history_search_keyword",
        ).strip()
        chat_history = st.session_state.get("chat_history", [])
        user_indexes = [
            index for index, message in enumerate(chat_history) if message.get("role") == "user"
        ]
        visible_count = 0
        for message_index in reversed(user_indexes[-12:]):
            question = str(chat_history[message_index].get("content", ""))
            if keyword and keyword.lower() not in question.lower():
                continue
            answer = ""
            if message_index + 1 < len(chat_history):
                next_message = chat_history[message_index + 1]
                if next_message.get("role") == "assistant":
                    answer = str(next_message.get("content", ""))
            st.markdown(
                f"""
                <details class="mla-drawer-item">
                    <summary><span>›</span><strong>{escape(truncate_text(question, 42))}</strong>
                    <small>当前会话 · 数学问答</small></summary>
                    <div class="mla-drawer-detail"><b>问题</b><p>{escape(question)}</p>
                    {f'<b>回答摘要</b><p>{escape(truncate_text(answer, 300))}</p>' if answer else ''}</div>
                </details>
                """,
                unsafe_allow_html=True,
            )
            visible_count += 1
        if not visible_count:
            st.caption("当前条件下没有历史提问。")

        st.markdown('<div class="mla-drawer-section">最近会话</div>', unsafe_allow_html=True)
        try:
            recent_sessions = get_recent_sessions(limit=6) if ENABLE_SQLITE_MEMORY else []
        except Exception:
            recent_sessions = []
        if not recent_sessions:
            st.caption("暂无已保存的历史会话。")
        else:
            for session in recent_sessions:
                session_id = str(session.get("session_id", ""))
                message_count = session.get("message_count", 0)
                updated_at = str(session.get("updated_at", ""))
                files = " · ".join(str(x) for x in session.get("file_names", [])[:3])
                st.markdown(
                    f"""
                    <details class="mla-drawer-item">
                        <summary><span>›</span><strong>{escape(session_id[:8])}</strong>
                        <small>{message_count} 条消息{(' · ' + escape(updated_at)) if updated_at else ''}</small></summary>
                        <div class="mla-drawer-detail"><p>{escape(files or '无关联资料')}</p></div>
                    </details>
                    """,
                    unsafe_allow_html=True,
                )
        if st.button("清空当前对话", key="history_clear_chat"):
            if ENABLE_SQLITE_MEMORY:
                try:
                    clear_session_memory(st.session_state.get("session_id", ""))
                except Exception:
                    pass
            reset_chat_state()
            st.rerun()


def render_materials_drawer():
    if not st.session_state.get("materials_drawer_open"):
        return

    st.markdown('<div class="mla-drawer-scrim"></div>', unsafe_allow_html=True)
    with st.container(key="mla_materials_drawer"):
        title_col, close_col = st.columns([5, 1])
        with title_col:
            st.markdown(
                """
                <div class="mla-drawer-title">
                    <strong>学习资料</strong>
                    <span>按需上传 · 不打断当前对话</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with close_col:
            if st.button("×", key="close_materials_drawer"):
                st.session_state["materials_drawer_open"] = False
                st.rerun()

        st.markdown(
            """
            <div class="mla-materials-intro">
                <strong>上传试卷、讲义或题目图片</strong>
                <span>支持 PDF、Word、TXT、PNG、JPG、WEBP。上传后，AI 会优先结合资料回答。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded_files = st.file_uploader(
            "上传资料",
            type=SUPPORTED_FILE_TYPES,
            accept_multiple_files=True,
            key="materials_drawer_uploader",
        )
        process_uploaded_files(uploaded_files)

        if st.session_state.get("vector_build_error"):
            st.warning(st.session_state["vector_build_error"])

        file_names = st.session_state.get("current_file_names", [])
        chunks = st.session_state.get("chunks", [])
        st.markdown('<div class="mla-drawer-section">当前资料</div>', unsafe_allow_html=True)
        if not file_names:
            st.caption("还没有上传资料。你仍然可以在主对话区直接聊天或提问。")
        else:
            per_file_chunks = max(1, len(chunks) // max(1, len(file_names)))
            for file_name in file_names:
                st.markdown(
                    f"""
                    <div class="mla-source-row drawer">
                        <span class="mla-source-icon">文</span>
                        <div class="mla-source-copy">
                            <strong>{escape(str(file_name))}</strong>
                            <span>{per_file_chunks} 个片段</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown(
            f"""
            <div class="mla-material-stats">
                <div><span>文件</span><strong>{len(file_names)}</strong></div>
                <div><span>Chunk</span><strong>{len(chunks)}</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("校正识别片段", key="materials_open_chunks", use_container_width=True):
            navigate("chunks")
            st.rerun()


def render_wrongbook_drawer():
    if not ENABLE_WRONGBOOK or not st.session_state.get("wrongbook_drawer_open"):
        return

    st.markdown('<div class="mla-drawer-scrim"></div>', unsafe_allow_html=True)
    with st.container(key="mla_wrongbook_drawer"):
        title_col, close_col = st.columns([5, 1])
        with title_col:
            st.markdown(
                """
                <div class="mla-drawer-title">
                    <strong>错题库</strong>
                    <span>悬浮抽屉 · 不离开当前学习上下文</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with close_col:
            if st.button("关闭", key="close_wrongbook_drawer"):
                st.session_state["wrongbook_drawer_open"] = False
                st.rerun()

        keyword = st.text_input(
            "查找错题",
            placeholder="搜索题干、解析或标签...",
            key="drawer_wrongbook_keyword",
        )
        col1, col2 = st.columns(2)
        with col1:
            question_type = st.selectbox(
                "题型", ["全部", *TYPE_OPTIONS], key="drawer_wrongbook_type"
            )
        with col2:
            difficulty = st.selectbox(
                "难度", ["全部", 1, 2, 3, 4, 5], key="drawer_wrongbook_difficulty"
            )
        filter_tag = st.text_input(
            "标签",
            placeholder="输入完整标签，例如：导数",
            key="drawer_wrongbook_tag",
        )
        review_status = st.selectbox(
            "复习状态",
            ["全部", "new", "reviewing", "mastered"],
            format_func=lambda value: {
                "全部": "全部",
                "new": "新错题",
                "reviewing": "复习中",
                "mastered": "已掌握",
            }.get(value, value),
            key="drawer_wrongbook_review_status",
        )
        due_only = st.checkbox(
            "只显示今天以前到期的错题", key="drawer_wrongbook_due_only"
        )

        try:
            wrong_questions = get_wrong_questions_filtered(
                question_type="" if question_type == "全部" else question_type,
                difficulty=None if difficulty == "全部" else difficulty,
                tag=filter_tag.strip(),
                keyword=keyword.strip(),
                review_status="" if review_status == "全部" else review_status,
                due_before=datetime.now().strftime("%Y-%m-%d") if due_only else None,
                limit=100,
            )
        except Exception as exc:
            wrong_questions = []
            st.error(f"读取错题库失败：{exc}")

        st.markdown(
            f'<div class="mla-wrongbook-count"><span>匹配数量</span><strong>{len(wrong_questions)}</strong></div>',
            unsafe_allow_html=True,
        )
        if not wrong_questions:
            st.caption("没有符合当前条件的错题。")
        else:
            status_labels = {"new": "新错题", "reviewing": "复习中", "mastered": "已掌握"}
            for wrong in wrong_questions[:30]:
                title = f"{wrong.get('type', '未分类')} · 难度 {wrong.get('difficulty', '')}"
                question = str(wrong.get("question_text") or "未保存题目正文。")
                analysis = str(wrong.get("analysis") or "")
                status = status_labels.get(wrong.get("review_status", "new"), "新错题")
                tags = " / ".join(str(x) for x in wrong.get("tags", []))
                st.markdown(
                    f"""
                    <details class="mla-drawer-item">
                        <summary><span>›</span><strong>{escape(title)}</strong>
                        <small>{escape(truncate_text(question, 34))}</small></summary>
                        <div class="mla-drawer-detail"><b>题目</b><p>{escape(question)}</p>
                        {f'<b>解析</b><p>{escape(analysis)}</p>' if analysis else ''}
                        <small>{escape(status)}{(' · ' + escape(tags)) if tags else ''}</small></div>
                    </details>
                    """,
                    unsafe_allow_html=True,
                )
        if st.button("清空筛选", key="clear_wrongbook_filters"):
            reset_wrongbook_filters()
            st.rerun()

        if wrong_questions:
            st.markdown('<div class="mla-drawer-section">PDF 导出</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="mla-pdf-export-card">
                    <strong>导出当前结果</strong>
                    <span>将当前筛选出的 {len(wrong_questions)} 道错题整理为 PDF。要导出全部错题，请先清空筛选。</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "生成筛选结果 PDF",
                key="export_filtered_wrongbook_pdf",
                use_container_width=True,
            ):
                selected_ids = [
                    str(item["id"])
                    for item in wrong_questions
                    if item.get("id")
                ]
                try:
                    st.session_state["wrongbook_filtered_pdf_path"] = (
                        export_wrong_questions_to_pdf_by_ids(selected_ids)
                    )
                    st.session_state["wrongbook_pdf_error"] = ""
                except Exception as exc:
                    st.session_state["wrongbook_filtered_pdf_path"] = ""
                    st.session_state["wrongbook_pdf_error"] = str(exc)

            if st.session_state.get("wrongbook_pdf_error"):
                st.warning(st.session_state["wrongbook_pdf_error"])

            filtered_pdf_path = st.session_state.get("wrongbook_filtered_pdf_path", "")
            if filtered_pdf_path and Path(filtered_pdf_path).exists():
                pdf_bytes, pdf_name = build_pdf_download_payload(filtered_pdf_path)
                st.download_button(
                    "下载当前筛选 PDF",
                    data=pdf_bytes,
                    file_name=pdf_name,
                    mime="application/pdf",
                    use_container_width=True,
                    key="download_filtered_wrongbook_pdf",
                )


def render_workspace_page():
    with st.container(key="mla_workspace_grid"):
        main_col, rail_col = st.columns([780, 356], gap="small")
        with main_col:
            render_chat_card()
            render_pending_card_flow()
        with rail_col:
            render_right_rail()


def render_upload_page():
    with st.container(key="mla_workspace_grid"):
        main_col, rail_col = st.columns([780, 356], gap="small")
        with main_col:
            render_upload_card("upload_page_uploader")
            with st.container(key="mla_chunk_card"):
                st.markdown("### 资料处理状态")
                file_names = st.session_state.get("current_file_names", [])
                chunks = st.session_state.get("chunks", [])
                vector_ready = st.session_state.get("vector_db") is not None
                c1, c2, c3 = st.columns(3)
                c1.metric("文件", len(file_names))
                c2.metric("Chunk", len(chunks))
                c3.metric("向量索引", "就绪" if vector_ready else "未就绪")
                if file_names:
                    for file_name in file_names:
                        st.write(f"- {file_name}")
                else:
                    st.info("上传资料后，这里会显示处理结果。")
                if st.session_state.get("vector_build_error"):
                    st.error(st.session_state["vector_build_error"])
        with rail_col:
            render_right_rail()


def render_chat_page():
    with st.container(key="mla_workspace_grid"):
        main_col, rail_col = st.columns([780, 356], gap="small")
        with main_col:
            render_chat_card()
            render_pending_card_flow()
        with rail_col:
            render_right_rail()


def render_chunks_page():
    with st.container(key="mla_workspace_grid"):
        main_col, rail_col = st.columns([780, 356], gap="small")
        with main_col:
            with st.container(key="mla_chunk_card"):
                st.markdown("### 校正资料片段")
                st.caption("如果资料识别不完整，可以修改对应片段，再继续问答。")
                chunks = st.session_state.get("chunks", [])
                if chunks:
                    render_chunk_debug_panel(chunks)
                else:
                    st.info("上传资料后，这里会出现可修改的片段。")
        with rail_col:
            render_right_rail()


def render_current_page():
    page = st.session_state.get("active_page", "workspace")
    if page == "chat":
        render_chat_page()
    elif page == "chunks":
        render_chunks_page()
    else:
        render_workspace_page()


render_left_navigation()
render_topbar()
render_current_page()
render_materials_drawer()
render_history_drawer()
render_wrongbook_drawer()
