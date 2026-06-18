from html import escape

import streamlit as st


def render_global_styles():
    st.markdown(
        """
        <style>
        :root {
            --mla-bg: #f3f5f8;
            --mla-panel: #ffffff;
            --mla-panel-soft: #f1f3f7;
            --mla-border: #dfe3eb;
            --mla-border-strong: #c8ced9;
            --mla-ink: #151922;
            --mla-muted: #626b7a;
            --mla-subtle: #8a93a3;
            --mla-primary: #4056d6;
            --mla-primary-soft: #edf0ff;
            --mla-amber-soft: #fff7df;
            --mla-amber: #a15c00;
            --mla-success: #138a43;
            --mla-warning: #b26a00;
            --mla-danger: #b42318;
            --mla-radius: 8px;
        }

        .stApp {
            background: var(--mla-bg);
            color: var(--mla-ink);
        }

        .block-container {
            max-width: 1320px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: #fbfbfc;
            border-right: 1px solid var(--mla-border);
        }

        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            letter-spacing: 0;
            color: var(--mla-ink);
        }

        h1, h2, h3 {
            letter-spacing: 0;
            color: var(--mla-ink);
        }

        h2 {
            margin-top: 1.2rem;
            font-size: 1.35rem;
        }

        h3 {
            font-size: 1.05rem;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--mla-border);
            border-radius: var(--mla-radius);
            background: var(--mla-panel);
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
            border-radius: var(--mla-radius);
            overflow: hidden;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: var(--mla-radius);
            border: 1px solid var(--mla-border-strong);
            background: var(--mla-panel);
            color: var(--mla-ink);
            font-weight: 520;
            min-height: 38px;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: var(--mla-primary);
            color: var(--mla-primary);
            background: var(--mla-primary-soft);
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            border-radius: var(--mla-radius);
        }

        .mla-shell-header {
            border: 1px solid var(--mla-border);
            background:
                linear-gradient(135deg, rgba(64, 86, 214, 0.08) 0%, rgba(255, 255, 255, 0) 42%),
                linear-gradient(180deg, #ffffff 0%, #f7f8fb 100%);
            border-radius: 14px;
            padding: 24px 26px;
            margin-bottom: 18px;
        }

        .mla-kicker {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--mla-primary);
            background: var(--mla-primary-soft);
            border: 1px solid #dfe3ff;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 650;
            margin-bottom: 12px;
        }

        .mla-title {
            margin: 0;
            font-size: 34px;
            line-height: 1.15;
            letter-spacing: 0;
            font-weight: 720;
            color: var(--mla-ink);
        }

        .mla-workbench-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.9fr) minmax(320px, 0.82fr);
            gap: 18px;
            align-items: start;
            margin-top: 4px;
        }

        .mla-workbench-main,
        .mla-workbench-rail {
            min-width: 0;
        }

        .mla-panel-shell {
            background: var(--mla-panel);
            border: 1px solid var(--mla-border);
            border-radius: 12px;
            padding: 18px 18px 14px;
            margin-bottom: 16px;
        }

        .mla-chat-stage {
            background:
                linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
            border: 1px solid var(--mla-border);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 16px;
        }

        .mla-chat-stage h2 {
            margin-top: 0;
        }

        .mla-rail-title {
            font-size: 13px;
            font-weight: 700;
            color: var(--mla-subtle);
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin: 2px 0 10px;
        }

        .mla-assist-card {
            background: var(--mla-panel);
            border: 1px solid var(--mla-border);
            border-radius: var(--mla-radius);
            padding: 14px;
            margin-bottom: 12px;
        }

        .mla-assist-card strong {
            display: block;
            color: var(--mla-ink);
            margin-bottom: 4px;
        }

        .mla-assist-card span {
            display: block;
            color: var(--mla-muted);
            font-size: 12px;
            line-height: 1.45;
        }

        .mla-subtitle {
            margin: 10px 0 0 0;
            max-width: 920px;
            color: var(--mla-muted);
            font-size: 15px;
            line-height: 1.6;
        }

        .mla-status-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 0 0 18px 0;
        }

        .mla-status-card {
            background: var(--mla-panel);
            border: 1px solid var(--mla-border);
            border-radius: var(--mla-radius);
            padding: 14px 16px;
        }

        .mla-status-label {
            color: var(--mla-subtle);
            font-size: 12px;
            line-height: 1.2;
            margin-bottom: 6px;
        }

        .mla-status-value {
            color: var(--mla-ink);
            font-size: 20px;
            font-weight: 680;
            line-height: 1.2;
        }

        .mla-status-note {
            color: var(--mla-muted);
            font-size: 12px;
            margin-top: 4px;
        }

        .mla-section-note {
            color: var(--mla-muted);
            font-size: 13px;
            line-height: 1.5;
            margin-top: -6px;
            margin-bottom: 12px;
        }

        .mla-sidebar-brand {
            border: 1px solid var(--mla-border);
            background: var(--mla-panel);
            border-radius: var(--mla-radius);
            padding: 12px;
            margin-bottom: 14px;
        }

        .mla-sidebar-brand strong {
            color: var(--mla-ink);
        }

        .mla-sidebar-brand span {
            display: block;
            color: var(--mla-muted);
            font-size: 12px;
            margin-top: 3px;
        }

        @media (max-width: 900px) {
            .mla-workbench-grid {
                grid-template-columns: 1fr;
            }
            .mla-status-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .mla-title {
                font-size: 28px;
            }
        }

        @media (max-width: 560px) {
            .mla-status-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(title):
    st.markdown(
        f"""
        <section class="mla-shell-header">
            <div class="mla-kicker">Conversation-first Math Workbench</div>
            <h1 class="mla-title">{title}</h1>
            <p class="mla-subtitle">
                以 AI 对话为主工作区，资料解析、Chunk 校正和错题管理作为辅助面板。
                目标是让用户先提问、再追溯来源、最后沉淀错题。
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_status_grid(items):
    cards = []

    for item in items:
        cards.append(
            '<div class="mla-status-card">'
            f'<div class="mla-status-label">{escape(str(item.get("label", "")))}</div>'
            f'<div class="mla-status-value">{escape(str(item.get("value", "")))}</div>'
            f'<div class="mla-status-note">{escape(str(item.get("note", "")))}</div>'
            "</div>"
        )

    st.markdown(
        f'<section class="mla-status-grid">{"".join(cards)}</section>',
        unsafe_allow_html=True,
    )


def render_section_note(text):
    st.markdown(
        f'<div class="mla-section-note">{text}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_brand(product_name, product_chinese_name, session_id):
    st.markdown(
        f"""
        <div class="mla-sidebar-brand">
            <strong>{product_name}</strong>
            <span>{product_chinese_name}</span>
            <span>Session {session_id}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def open_workbench_layout():
    st.markdown(
        """
        <section class="mla-workbench-grid">
            <div class="mla-workbench-main">
        """,
        unsafe_allow_html=True,
    )


def switch_to_workbench_rail():
    st.markdown(
        """
            </div>
            <aside class="mla-workbench-rail">
        """,
        unsafe_allow_html=True,
    )


def close_workbench_layout():
    st.markdown(
        """
            </aside>
        </section>
        """,
        unsafe_allow_html=True,
    )


def open_panel_shell(extra_class=""):
    st.markdown(
        f'<section class="mla-panel-shell {extra_class}">',
        unsafe_allow_html=True,
    )


def close_panel_shell():
    st.markdown("</section>", unsafe_allow_html=True)


def open_chat_stage():
    st.markdown('<section class="mla-chat-stage">', unsafe_allow_html=True)


def close_chat_stage():
    st.markdown("</section>", unsafe_allow_html=True)


def render_assist_card(title, body):
    st.markdown(
        f"""
        <div class="mla-assist-card">
            <strong>{title}</strong>
            <span>{body}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
