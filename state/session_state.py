import uuid

import streamlit as st


def new_session_id():
    return uuid.uuid4().hex[:12]


def init_session_state():
    defaults = {
        "chat_history": list,
        "vector_db": lambda: None,
        "current_file_key": str,
        "current_file_names": list,
        "documents": list,
        "chunks": list,
        "session_id": new_session_id,
        "memory_loaded": lambda: False,
        "last_log_row": lambda: None,
        "last_card_results": list,
        "last_card_source_info": dict,
        "last_card_saved": lambda: False,
        "pending_card_question_text": str,
        "pending_card_items": list,
        "pending_card_source_info": dict,
        "editable_question_text": str,
        "editable_math_items": list,
        "edit_instruction": str,
        "vector_build_error": str,
        "vector_build_file_key": str,
        # Figma UI states
        "active_page": lambda: "workspace",
        "materials_drawer_open": lambda: False,
        "history_drawer_open": lambda: False,
        "wrongbook_drawer_open": lambda: False,
        "upload_processing": lambda: False,
        "upload_process_attempted_key": str,
        "upload_process_stage": str,
        "upload_process_progress": lambda: 0,
        "drawer_wrongbook_keyword": str,
        "drawer_wrongbook_type": lambda: "全部",
        "drawer_wrongbook_difficulty": lambda: "全部",
        "drawer_wrongbook_tag": str,
        "drawer_wrongbook_review_status": lambda: "全部",
        "drawer_wrongbook_due_only": lambda: False,
        "history_search_keyword": str,
    }

    for key, factory in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = factory()


def close_drawers():
    st.session_state["materials_drawer_open"] = False
    st.session_state["history_drawer_open"] = False
    st.session_state["wrongbook_drawer_open"] = False


def reset_document_state():
    st.session_state["current_file_key"] = ""
    st.session_state["current_file_names"] = []
    st.session_state["documents"] = []
    st.session_state["chunks"] = []
    st.session_state["vector_db"] = None
    st.session_state["vector_build_error"] = ""
    st.session_state["vector_build_file_key"] = ""
    st.session_state["upload_process_attempted_key"] = ""
    st.session_state["upload_process_stage"] = ""
    st.session_state["upload_process_progress"] = 0
    st.session_state["upload_processing"] = False


def reset_card_state():
    st.session_state["last_card_results"] = []
    st.session_state["last_card_source_info"] = {}
    st.session_state["last_card_saved"] = False
    st.session_state["pending_card_question_text"] = ""
    st.session_state["pending_card_items"] = []
    st.session_state["pending_card_source_info"] = {}
    st.session_state["editable_question_text"] = ""
    st.session_state["editable_math_items"] = []


def reset_chat_state():
    st.session_state["chat_history"] = []
    st.session_state["last_log_row"] = None
    reset_card_state()


def start_new_file_session(file_key, file_names):
    st.session_state["current_file_key"] = file_key
    st.session_state["current_file_names"] = list(file_names)
    st.session_state["documents"] = []
    st.session_state["chunks"] = []
    st.session_state["vector_db"] = None
    st.session_state["vector_build_error"] = ""
    st.session_state["vector_build_file_key"] = ""
    st.session_state["upload_process_attempted_key"] = ""
    st.session_state["upload_process_stage"] = ""
    st.session_state["upload_process_progress"] = 0
    st.session_state["upload_processing"] = False
    reset_chat_state()

    # 换文件时开启新 session，避免不同资料的问答互相污染。
    st.session_state["session_id"] = new_session_id()
    st.session_state["memory_loaded"] = True
