from html import escape

import streamlit as st


def render_global_styles():
    st.markdown(
        r"""
        <style>
        :root {
            --mla-bg: #f8f5ec;
            --mla-paper: #fffef9;
            --mla-white: #ffffff;
            --mla-ink: #26211a;
            --mla-muted: #6e6657;
            --mla-subtle: #948c7d;
            --mla-border: #dbd1ba;
            --mla-accent: #ba5c33;
            --mla-accent-soft: #f5dec7;
            --mla-sage: #6b8c6e;
            --mla-sage-soft: #e0ebdb;
            --mla-blue: #476b8f;
            --mla-blue-soft: #dee8f2;
            --mla-dark: #2e291f;
            --mla-dark-soft: #3d3629;
            --mla-nav-active: #54402e;
        }

        html, body, [class*="css"] {
            font-family: Inter, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"] {
            background: #ffffff !important;
            color: var(--mla-ink);
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        footer {
            display: none !important;
        }

        .block-container {
            box-sizing: border-box !important;
            width: auto !important;
            max-width: none !important;
            min-height: 100vh !important;
            padding: 100px 24px 24px 260px !important;
        }

        p, h1, h2, h3, h4, h5, h6 {
            color: var(--mla-ink);
        }

        /* ---------- generic Streamlit controls ---------- */
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            min-height: 40px;
            border: 1px solid var(--mla-border) !important;
            border-radius: 10px !important;
            background: var(--mla-paper) !important;
            color: var(--mla-ink) !important;
            box-shadow: none !important;
            font-size: 12px !important;
            font-weight: 600 !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            border-color: var(--mla-accent) !important;
            color: var(--mla-accent) !important;
        }

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label,
        .stCheckbox label,
        .stSelectSlider label {
            color: var(--mla-muted) !important;
            font-size: 11px !important;
            font-weight: 500 !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stDateInput input {
            min-height: 40px !important;
            border: 1px solid var(--mla-border) !important;
            border-radius: 10px !important;
            background: #fff !important;
            color: var(--mla-ink) !important;
            box-shadow: none !important;
            font-size: 12px !important;
        }

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: var(--mla-subtle) !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border-color: var(--mla-accent) !important;
            box-shadow: 0 0 0 2px rgba(186, 92, 51, .10) !important;
        }

        [data-testid="stCaptionContainer"] p,
        .stCaptionContainer p {
            color: var(--mla-muted) !important;
            font-size: 10px !important;
            line-height: 1.45 !important;
        }

        /* ---------- exact 236px navigation ---------- */
        div[class*="st-key-mla_left_navigation"] {
            position: fixed !important;
            inset: 0 auto 0 0 !important;
            z-index: 3000 !important;
            box-sizing: border-box !important;
            width: 236px !important;
            height: 100vh !important;
            padding: 20px !important;
            overflow: hidden !important;
            background: var(--mla-dark) !important;
        }

        div[class*="st-key-mla_left_navigation"] > div,
        div[class*="st-key-mla_left_navigation"] [data-testid="stVerticalBlock"] {
            gap: 18px !important;
        }

        div[class*="st-key-mla_left_navigation"] [data-testid="stElementContainer"] {
            margin: 0 !important;
        }

        .mla-nav-brand {
            box-sizing: border-box;
            width: 196px;
            height: 42px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 8px;
            overflow: hidden;
            border: 1px solid #574d3d;
            border-radius: 12px;
            background: var(--mla-dark-soft);
        }

        .mla-nav-logo {
            width: 34px;
            height: 34px;
            flex: 0 0 34px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            background: var(--mla-accent);
            color: #ffffff;
            font-size: 14px;
            font-weight: 800;
        }

        .mla-nav-brand-copy {
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 1px;
            line-height: 1.2;
        }

        .mla-nav-brand-copy strong {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #fff4e6;
            font-size: 14px;
            font-weight: 600;
        }

        .mla-nav-brand-copy span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #c7bdab;
            font-size: 9px;
        }

        div[class*="st-key-mla_left_navigation"] .stButton > button {
            width: 196px !important;
            height: 44px !important;
            min-height: 44px !important;
            justify-content: flex-start !important;
            padding: 0 12px !important;
            border: 0 !important;
            border-radius: 12px !important;
            background: transparent !important;
            color: #dbd1bf !important;
            box-shadow: none !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            line-height: 1 !important;
        }

        div[class*="st-key-mla_left_navigation"] .stButton > button:hover {
            background: var(--mla-dark-soft) !important;
            color: #ffffff !important;
        }

        div[class*="st-key-mla_left_navigation"] .stButton > button[kind="primary"] {
            background: var(--mla-nav-active) !important;
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        .mla-daily-goal {
            position: fixed;
            left: 20px;
            bottom: 20px;
            box-sizing: border-box;
            width: 196px;
            height: 110px;
            padding: 14px;
            border-radius: 14px;
            background: var(--mla-dark-soft);
            z-index: 3001;
        }

        .mla-daily-goal strong {
            display: block;
            margin-bottom: 8px;
            color: var(--mla-accent-soft);
            font-size: 12px;
            font-weight: 600;
        }

        .mla-daily-goal span {
            display: block;
            margin-bottom: 14px;
            color: #c7bdab;
            font-size: 11px;
        }

        .mla-daily-goal small {
            display: block;
            margin-top: 10px;
            color: #eadfce;
            font-size: 10px;
            font-weight: 600;
            opacity: 1;
        }

        .mla-goal-track {
            height: 6px;
            overflow: hidden;
            border-radius: 99px;
            background: #574d3d;
        }

        .mla-goal-value {
            width: 62%;
            height: 100%;
            border-radius: 99px;
            background: var(--mla-accent);
        }

        /* ---------- exact 76px top bar ---------- */
        div[class*="st-key-mla_topbar"] {
            position: fixed !important;
            left: 236px !important;
            right: 0 !important;
            top: 0 !important;
            z-index: 2500 !important;
            box-sizing: border-box !important;
            height: 76px !important;
            padding: 16px 24px !important;
            overflow: visible !important;
            background: var(--mla-paper) !important;
            border-bottom: 1px solid var(--mla-border) !important;
        }

        div[class*="st-key-mla_topbar"] > div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        div[class*="st-key-mla_topbar"] [data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: 750px 90px 34px 34px !important;
            gap: 14px !important;
            align-items: center !important;
            justify-content: start !important;
        }

        div[class*="st-key-mla_topbar"] [data-testid="column"] {
            width: auto !important;
            min-width: 0 !important;
            flex: none !important;
            padding: 0 !important;
        }

        .mla-top-title {
            height: 44px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            gap: 1px;
            overflow: hidden;
        }

        .mla-top-title strong {
            color: var(--mla-ink);
            font-size: 22px;
            font-weight: 700;
            line-height: 1.15;
        }

        .mla-top-title span {
            color: var(--mla-muted);
            font-size: 11px;
            line-height: 1.45;
        }

        .mla-streak {
            box-sizing: border-box;
            width: 90px;
            height: 29px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: var(--mla-sage-soft);
            color: var(--mla-sage);
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }

        div[class*="st-key-mla_topbar"] [data-testid="stPopover"] > button,
        div[class*="st-key-mla_topbar"] .stButton > button {
            width: 34px !important;
            height: 34px !important;
            min-height: 34px !important;
            padding: 0 !important;
            border: 0 !important;
            border-radius: 10px !important;
            background: var(--mla-blue-soft) !important;
            color: var(--mla-ink) !important;
            font-size: 14px !important;
            font-weight: 700 !important;
        }

        div[class*="st-key-mla_topbar"] [data-testid="stPopover"] > button span,
        div[class*="st-key-mla_topbar"] [data-testid="stPopover"] > button svg {
            display: none !important;
        }

        div[class*="st-key-mla_topbar"] [data-testid="stPopover"] > button::after {
            content: "?";
            display: grid;
            place-items: center;
            width: 100%;
            height: 100%;
        }

        .mla-avatar {
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            background: var(--mla-accent-soft);
            color: var(--mla-ink);
            font-size: 14px;
            font-weight: 700;
        }

        /* ---------- exact 780 / 356 / 20 workspace grid ---------- */
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: 780px 356px !important;
            gap: 20px !important;
            align-items: start !important;
            justify-content: start !important;
        }

        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: auto !important;
            min-width: 0 !important;
            flex: none !important;
            padding: 0 !important;
        }

        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1),
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) > div,
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) > div > div[data-testid="stVerticalBlock"] {
            width: 780px !important;
            max-width: 780px !important;
            flex: 0 0 780px !important;
        }

        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2),
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div,
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div > div[data-testid="stVerticalBlock"] {
            width: 356px !important;
            max-width: 356px !important;
            flex: 0 0 356px !important;
        }

        div[class*="st-key-mla_workspace_grid"] [data-testid="column"] > div[data-testid="stVerticalBlock"] {
            gap: 16px !important;
        }

        /* ---------- upload card: node 2:48 ---------- */
        div[class*="st-key-mla_upload_card"] {
            position: relative !important;
            box-sizing: border-box !important;
            width: 780px !important;
            height: 150px !important;
            min-height: 150px !important;
            padding: 18px !important;
            overflow: hidden !important;
            border: 1px solid var(--mla-border) !important;
            border-radius: 16px !important;
            background: var(--mla-paper) !important;
        }

        div[class*="st-key-mla_upload_card"] > div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        .mla-upload-header {
            position: relative;
            height: 110px;
        }

        .mla-card-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .mla-upload-header .mla-card-icon {
            position: absolute;
            top: 29px;
            left: 0;
        }

        .mla-upload-header .mla-card-title {
            position: absolute;
            top: 0;
            left: 70px;
        }

        .mla-card-icon {
            width: 34px;
            height: 34px;
            flex: 0 0 34px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            background: var(--mla-sage-soft);
            color: var(--mla-ink);
            font-size: 14px;
            font-weight: 700;
        }

        .mla-card-icon.upload {
            width: 56px;
            height: 56px;
            flex-basis: 56px;
            background: var(--mla-accent-soft);
        }

        .mla-card-title {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .mla-card-title strong {
            color: var(--mla-ink);
            font-size: 16px;
            font-weight: 600;
            line-height: 1.45;
        }

        .mla-card-title span {
            color: var(--mla-muted);
            font-size: 11px;
            line-height: 1.45;
        }

        .mla-card-title.big strong {
            font-size: 18px;
        }

        .mla-card-title.big span {
            font-size: 12px;
        }

        div[class*="st-key-mla_upload_card"] div[class*="st-key-main_uploader"],
        div[class*="st-key-mla_upload_card"] div[class*="st-key-upload_page_uploader"] {
            position: absolute !important;
            left: 88px !important;
            top: 72px !important;
            width: 86px !important;
            height: 29px !important;
            z-index: 2 !important;
        }

        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploader"] {
            position: static !important;
            width: 86px !important;
        }

        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploaderDropzone"] {
            min-height: 29px !important;
            height: 29px !important;
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
        }

        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploaderDropzoneInstructions"],
        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploaderDropzone"] small,
        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploaderFile"] {
            display: none !important;
        }

        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploaderDropzone"] button {
            width: 64px !important;
            height: 29px !important;
            min-height: 29px !important;
            padding: 0 8px !important;
            border: 0 !important;
            border-radius: 999px !important;
            background: var(--mla-accent) !important;
            color: transparent !important;
            box-shadow: none !important;
            font-size: 0 !important;
            position: relative !important;
            overflow: hidden !important;
        }

        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploaderDropzone"] button * {
            opacity: 0 !important;
            font-size: 0 !important;
        }

        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploaderDropzone"] button::after {
            content: "选择文件";
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 12px;
            font-weight: 500;
        }

        /* ---------- chat card: node 2:56 ---------- */
        div[class*="st-key-mla_chat_card"] {
            box-sizing: border-box !important;
            width: 780px !important;
            min-height: 590px !important;
            height: calc(100vh - 266px) !important;
            max-height: 727px !important;
            padding: 20px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            border: 1px solid var(--mla-border) !important;
            border-radius: 16px !important;
            background: var(--mla-paper) !important;
        }

        div[class*="st-key-mla_chat_card"] > div[data-testid="stVerticalBlock"] {
            gap: 16px !important;
        }

        .mla-chat-head {
            height: 46px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .mla-source-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 29px;
            padding: 0 8px;
            border-radius: 999px;
            background: var(--mla-blue-soft);
            color: var(--mla-blue);
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }

        .mla-chat-welcome {
            box-sizing: border-box;
            width: 100%;
            min-height: 76px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            border-radius: 14px;
            background: var(--mla-sage-soft);
        }

        .mla-chat-welcome strong,
        .mla-chat-welcome span {
            font-size: 13px;
            line-height: 1.45;
        }

        .mla-chat-welcome strong {
            color: var(--mla-ink);
            font-weight: 500;
        }

        .mla-chat-welcome span {
            color: var(--mla-muted);
        }

        div[class*="st-key-mla_chat_user_"] {
            box-sizing: border-box;
            width: 100%;
            padding: 14px !important;
            border-radius: 14px !important;
            background: var(--mla-accent-soft) !important;
        }

        div[class*="st-key-mla_chat_assistant_"] {
            box-sizing: border-box;
            width: 100%;
            padding: 14px !important;
            border: 1px solid var(--mla-border) !important;
            border-radius: 14px !important;
            background: var(--mla-paper) !important;
        }

        div[class*="st-key-mla_chat_user_"] p,
        div[class*="st-key-mla_chat_assistant_"] p {
            margin: 0 !important;
            font-size: 13px !important;
            line-height: 1.55 !important;
        }

        div[class*="st-key-mla_chat_composer"] {
            position: sticky !important;
            bottom: 0 !important;
            z-index: 4 !important;
            box-sizing: border-box !important;
            width: 100% !important;
            min-height: 52px !important;
            padding: 8px 10px !important;
            border: 1px solid var(--mla-border) !important;
            border-radius: 14px !important;
            background: #fff !important;
        }

        div[class*="st-key-mla_chat_composer"] form,
        div[class*="st-key-mla_chat_composer"] [data-testid="stForm"] {
            border: 0 !important;
            padding: 0 !important;
        }

        div[class*="st-key-mla_chat_composer"] [data-testid="stHorizontalBlock"] {
            gap: 10px !important;
            align-items: center !important;
        }

        div[class*="st-key-mla_chat_composer"] .stTextInput input {
            min-height: 34px !important;
            height: 34px !important;
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            font-size: 13px !important;
        }

        div[class*="st-key-mla_chat_composer"] [data-testid="stFormSubmitButton"] > button {
            width: 34px !important;
            height: 34px !important;
            min-height: 34px !important;
            padding: 0 !important;
            border: 0 !important;
            border-radius: 10px !important;
            background: var(--mla-accent) !important;
            color: var(--mla-ink) !important;
            font-size: 14px !important;
            font-weight: 700 !important;
        }

        /* ---------- right rail ---------- */
        div[class*="st-key-mla_today_plan"],
        div[class*="st-key-mla_sources_card"],
        div[class*="st-key-mla_review_card"],
        div[class*="st-key-mla_study_tip"] {
            box-sizing: border-box !important;
            width: 356px !important;
            padding: 16px !important;
            overflow: hidden !important;
            border: 1px solid var(--mla-border) !important;
            border-radius: 16px !important;
            background: var(--mla-paper) !important;
        }

        div[class*="st-key-mla_today_plan"] {
            min-height: 218px !important;
        }

        div[class*="st-key-mla_sources_card"] {
            min-height: 234px !important;
        }

        div[class*="st-key-mla_review_card"] {
            min-height: 220px !important;
        }

        div[class*="st-key-mla_study_tip"] {
            min-height: 126px !important;
            border: 0 !important;
            background: #332e24 !important;
        }

        div[class*="st-key-mla_today_plan"] > div[data-testid="stVerticalBlock"],
        div[class*="st-key-mla_sources_card"] > div[data-testid="stVerticalBlock"],
        div[class*="st-key-mla_review_card"] > div[data-testid="stVerticalBlock"],
        div[class*="st-key-mla_study_tip"] > div[data-testid="stVerticalBlock"] {
            gap: 12px !important;
        }

        .mla-card-kicker {
            color: var(--mla-ink);
            font-size: 15px;
            font-weight: 600;
            line-height: 1.45;
        }

        .mla-plan-row {
            height: 34px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .mla-plan-dot {
            width: 10px;
            height: 10px;
            flex: 0 0 10px;
            border-radius: 50%;
            background: var(--mla-border);
        }

        .mla-plan-dot.done { background: var(--mla-sage); }
        .mla-plan-dot.active { background: var(--mla-accent); }

        .mla-plan-copy {
            display: flex;
            flex-direction: column;
            gap: 1px;
        }

        .mla-plan-copy strong {
            color: var(--mla-ink);
            font-size: 12px;
            font-weight: 500;
        }

        .mla-plan-copy span {
            color: var(--mla-muted);
            font-size: 10px;
        }

        .mla-source-row {
            box-sizing: border-box;
            width: 324px;
            height: 62px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            border-radius: 12px;
            background: var(--mla-bg);
        }

        .mla-source-icon {
            width: 34px;
            height: 34px;
            flex: 0 0 34px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            background: var(--mla-blue-soft);
            color: var(--mla-ink);
            font-size: 14px;
            font-weight: 700;
        }

        .mla-source-copy {
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 1px;
        }

        .mla-source-copy strong {
            max-width: 250px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--mla-ink);
            font-size: 12px;
            font-weight: 500;
        }

        .mla-source-copy span {
            color: var(--mla-muted);
            font-size: 10px;
        }

        .mla-empty-note {
            min-height: 62px;
            display: flex;
            align-items: center;
            padding: 10px;
            border-radius: 12px;
            background: var(--mla-bg);
            color: var(--mla-muted);
            font-size: 11px;
        }

        div[class*="st-key-mla_sources_card"] .stButton > button,
        div[class*="st-key-mla_review_card"] .stButton > button {
            width: auto !important;
            height: 29px !important;
            min-height: 29px !important;
            padding: 0 8px !important;
            border: 0 !important;
            border-radius: 999px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
        }

        div[class*="st-key-mla_sources_card"] .stButton > button {
            background: var(--mla-accent-soft) !important;
            color: var(--mla-accent) !important;
        }

        div[class*="st-key-mla_review_card"] .stButton > button {
            background: var(--mla-sage-soft) !important;
            color: var(--mla-sage) !important;
        }

        div[class*="st-key-mla_review_card"] [data-testid="stHorizontalBlock"] {
            gap: 8px !important;
        }

        div[class*="st-key-mla_review_card"] [data-testid="column"] {
            width: 101px !important;
            flex: 0 0 101px !important;
            padding: 0 !important;
        }

        div[class*="st-key-mla_review_card"] [data-testid="stMetric"] {
            box-sizing: border-box;
            width: 101px;
            height: 76px;
            padding: 10px;
            border-radius: 12px;
            background: var(--mla-bg);
        }

        div[class*="st-key-mla_review_card"] [data-testid="stMetricValue"] {
            color: var(--mla-ink);
            font-size: 20px;
            font-weight: 700;
            line-height: 1.45;
        }

        div[class*="st-key-mla_review_card"] [data-testid="stMetricLabel"] {
            color: var(--mla-muted);
            font-size: 10px;
        }

        div[class*="st-key-mla_study_tip"] .mla-card-kicker,
        div[class*="st-key-mla_study_tip"] strong,
        div[class*="st-key-mla_study_tip"] p {
            color: #ffffff !important;
        }

        div[class*="st-key-mla_study_tip"] .mla-card-kicker {
            color: var(--mla-accent-soft) !important;
            font-size: 12px;
        }

        div[class*="st-key-mla_study_tip"] strong {
            font-size: 13px;
            font-weight: 500;
        }

        div[class*="st-key-mla_study_tip"] [data-testid="stCaptionContainer"] p {
            color: #c7bdab !important;
            font-size: 11px !important;
        }

        /* ---------- drawer overlay: nodes 2:275 and 2:461 ---------- */
        .mla-drawer-scrim {
            position: fixed;
            left: 236px;
            right: 0;
            top: 0;
            bottom: 0;
            z-index: 4000;
            background: rgba(31, 26, 20, .18);
        }

        div[class*="st-key-mla_history_drawer"],
        div[class*="st-key-mla_wrongbook_drawer"] {
            position: fixed !important;
            left: 236px !important;
            top: 0 !important;
            bottom: 0 !important;
            z-index: 4100 !important;
            box-sizing: border-box !important;
            width: 390px !important;
            height: 100vh !important;
            padding: 20px !important;
            overflow-x: hidden !important;
            overflow-y: auto !important;
            background: var(--mla-paper) !important;
            box-shadow: 10px 0 32px rgba(26, 20, 13, .18) !important;
        }

        div[class*="st-key-mla_history_drawer"] > div[data-testid="stVerticalBlock"],
        div[class*="st-key-mla_wrongbook_drawer"] > div[data-testid="stVerticalBlock"] {
            gap: 14px !important;
        }

        div[class*="st-key-mla_history_drawer"] [data-testid="stHorizontalBlock"]:first-child,
        div[class*="st-key-mla_wrongbook_drawer"] [data-testid="stHorizontalBlock"]:first-child {
            display: grid !important;
            grid-template-columns: 295px 40px !important;
            gap: 10px !important;
            align-items: center !important;
        }

        div[class*="st-key-mla_history_drawer"] [data-testid="stHorizontalBlock"]:first-child > [data-testid="column"],
        div[class*="st-key-mla_wrongbook_drawer"] [data-testid="stHorizontalBlock"]:first-child > [data-testid="column"] {
            width: auto !important;
            min-width: 0 !important;
            flex: none !important;
            padding: 0 !important;
        }

        .mla-drawer-title {
            height: 44px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .mla-drawer-title strong {
            color: var(--mla-ink);
            font-size: 18px;
            font-weight: 700;
            line-height: 1.45;
        }

        .mla-drawer-title span {
            color: var(--mla-muted);
            font-size: 10px;
            line-height: 1.45;
        }

        div[class*="st-key-mla_history_drawer"] button[kind="secondary"],
        div[class*="st-key-mla_wrongbook_drawer"] button[kind="secondary"] {
            width: auto !important;
            height: 29px !important;
            min-height: 29px !important;
            padding: 0 8px !important;
            border: 0 !important;
            border-radius: 999px !important;
            background: var(--mla-bg) !important;
            color: var(--mla-muted) !important;
            font-size: 12px !important;
            font-weight: 500 !important;
        }

        div[class*="st-key-mla_history_drawer"] .stTextInput,
        div[class*="st-key-mla_wrongbook_drawer"] .stTextInput,
        div[class*="st-key-mla_wrongbook_drawer"] .stSelectbox {
            width: 350px !important;
        }

        div[class*="st-key-mla_wrongbook_drawer"] [data-testid="stHorizontalBlock"]:not(:first-child) {
            gap: 10px !important;
        }

        div[class*="st-key-mla_wrongbook_drawer"] [data-testid="stHorizontalBlock"]:not(:first-child) > [data-testid="column"] {
            width: 170px !important;
            flex: 0 0 170px !important;
            padding: 0 !important;
        }

        .mla-drawer-section {
            color: var(--mla-muted);
            font-size: 12px;
            font-weight: 600;
        }

        details.mla-drawer-item {
            box-sizing: border-box;
            width: 320px;
            min-height: 58px;
            border: 1px solid var(--mla-border);
            border-radius: 12px;
            background: #ffffff;
            overflow: hidden;
        }

        details.mla-drawer-item summary {
            position: relative;
            box-sizing: border-box;
            min-height: 56px;
            padding: 10px 12px 7px 27px;
            list-style: none;
            cursor: pointer;
        }

        details.mla-drawer-item summary::-webkit-details-marker {
            display: none;
        }

        details.mla-drawer-item summary > span {
            position: absolute;
            left: 12px;
            top: 9px;
            color: var(--mla-accent);
            font-size: 16px;
            font-weight: 600;
            transition: transform .15s ease;
        }

        details.mla-drawer-item[open] summary > span {
            transform: rotate(90deg);
        }

        details.mla-drawer-item summary strong {
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--mla-ink);
            font-size: 12px;
            font-weight: 500;
            line-height: 1.45;
        }

        details.mla-drawer-item summary small {
            display: block;
            margin-top: 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--mla-muted);
            font-size: 10px;
            line-height: 1.45;
        }

        .mla-drawer-detail {
            padding: 0 12px 12px;
            border-top: 1px solid #eee8dc;
        }

        .mla-drawer-detail b {
            display: block;
            margin-top: 10px;
            color: var(--mla-accent);
            font-size: 11px;
        }

        .mla-drawer-detail p,
        .mla-drawer-detail small {
            margin: 4px 0 0;
            color: var(--mla-muted);
            font-size: 11px;
            line-height: 1.55;
            white-space: normal;
        }

        .mla-wrongbook-count {
            box-sizing: border-box;
            width: 350px;
            height: 58px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 12px;
            border-radius: 12px;
            background: var(--mla-sage-soft);
        }

        .mla-wrongbook-count span {
            color: var(--mla-sage);
            font-size: 11px;
            font-weight: 500;
        }

        .mla-wrongbook-count strong {
            color: var(--mla-ink);
            font-size: 22px;
            font-weight: 700;
            line-height: 1;
        }

        .mla-pdf-export-card {
            box-sizing: border-box;
            width: 350px;
            padding: 14px;
            border: 1px solid var(--mla-border);
            border-radius: 14px;
            background: var(--mla-bg);
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .mla-pdf-export-card strong {
            color: var(--mla-ink);
            font-size: 14px;
            font-weight: 700;
        }

        .mla-pdf-export-card span {
            color: var(--mla-muted);
            font-size: 12px;
            line-height: 1.55;
        }

        div[class*="st-key-mla_history_drawer"] .stButton:last-child > button {
            background: var(--mla-accent-soft) !important;
            color: var(--mla-accent) !important;
        }

        /* ---------- upload processing modal: node 2:653 ---------- */
        .mla-processing-modal {
            position: fixed;
            left: calc(236px + (100vw - 236px) / 2 - 280px);
            top: 50%;
            z-index: 5000;
            transform: translateY(-50%);
            box-sizing: border-box;
            width: 560px;
            height: 360px;
            padding: 24px;
            overflow: hidden;
            border: 1px solid var(--mla-border);
            border-radius: 20px;
            background: var(--mla-paper);
            box-shadow: 0 16px 40px rgba(26, 20, 13, .18);
        }

        .mla-processing-modal h3 {
            margin: 0 0 6px;
            color: var(--mla-ink);
            font-size: 20px;
            font-weight: 700;
            line-height: 1.45;
        }

        .mla-processing-modal > p {
            margin: 0 0 16px;
            color: var(--mla-muted);
            font-size: 12px;
            line-height: 1.45;
        }

        .mla-processing-file {
            box-sizing: border-box;
            width: 512px;
            height: 70px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 14px;
            margin-bottom: 16px;
            border-radius: 12px;
            background: var(--mla-bg);
        }

        .mla-file-type {
            display: inline-flex;
            align-items: center;
            height: 29px;
            padding: 0 8px;
            border-radius: 999px;
            background: var(--mla-accent-soft);
            color: var(--mla-accent);
            font-size: 12px;
            font-weight: 500;
        }

        .mla-processing-file > div {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .mla-processing-file strong {
            max-width: 410px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--mla-ink);
            font-size: 13px;
            font-weight: 600;
        }

        .mla-processing-file span:not(.mla-file-type) {
            color: var(--mla-muted);
            font-size: 10px;
        }

        .mla-processing-track {
            width: 512px;
            height: 10px;
            overflow: hidden;
            margin-bottom: 10px;
            border-radius: 99px;
            background: var(--mla-border);
        }

        .mla-processing-value {
            height: 100%;
            border-radius: 99px;
            background: var(--mla-accent);
        }

        .mla-processing-label {
            margin-bottom: 14px;
            color: var(--mla-accent);
            font-size: 11px;
            font-weight: 500;
        }

        .mla-processing-steps {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .mla-processing-steps span {
            font-size: 11px;
            line-height: 1.45;
        }

        .mla-processing-steps .done { color: var(--mla-sage); }
        .mla-processing-steps .active { color: var(--mla-accent); font-weight: 500; }
        .mla-processing-steps .pending { color: var(--mla-muted); }

        /* ---------- auxiliary routed cards and editor ---------- */
        div[class*="st-key-mla_chunk_card"],
        div[class*="st-key-mla_card_editor_generate"],
        div[class*="st-key-mla_card_editor_form"],
        div[class*="st-key-mla_card_editor_save"] {
            box-sizing: border-box;
            width: 780px;
            padding: 20px;
            border: 1px solid var(--mla-border);
            border-radius: 16px;
            background: var(--mla-paper);
        }

        /* ---------- responsive fallback ---------- */
        @media (max-width: 1220px) {
            .block-container {
                padding-left: 256px !important;
                padding-right: 20px !important;
            }

            div[class*="st-key-mla_workspace_grid"] [data-testid="stHorizontalBlock"]:first-child {
                grid-template-columns: minmax(0, 1fr) 320px !important;
            }

            div[class*="st-key-mla_upload_card"],
            div[class*="st-key-mla_chat_card"] {
                width: 100% !important;
            }

            div[class*="st-key-mla_today_plan"],
            div[class*="st-key-mla_sources_card"],
            div[class*="st-key-mla_review_card"],
            div[class*="st-key-mla_study_tip"] {
                width: 320px !important;
            }

            .mla-source-row {
                width: 288px;
            }

            div[class*="st-key-mla_topbar"] [data-testid="stHorizontalBlock"] {
                grid-template-columns: minmax(360px, 1fr) 90px 34px 34px !important;
            }
        }

        @media (max-width: 900px) {
            div[class*="st-key-mla_left_navigation"] {
                width: 76px !important;
                padding: 16px 10px !important;
            }

            .mla-nav-brand {
                width: 56px;
                justify-content: center;
                background: transparent;
            }

            .mla-nav-brand-copy,
            .mla-daily-goal {
                display: none;
            }

            div[class*="st-key-mla_left_navigation"] .stButton > button {
                width: 56px !important;
                overflow: hidden;
                color: transparent !important;
                font-size: 0 !important;
                justify-content: center !important;
            }

            div[class*="st-key-mla_topbar"] {
                left: 76px !important;
            }

            .block-container {
                padding: 96px 16px 24px 92px !important;
            }

            div[class*="st-key-mla_workspace_grid"] [data-testid="stHorizontalBlock"]:first-child {
                display: flex !important;
                flex-direction: column !important;
            }

            div[class*="st-key-mla_today_plan"],
            div[class*="st-key-mla_sources_card"],
            div[class*="st-key-mla_review_card"],
            div[class*="st-key-mla_study_tip"] {
                width: 100% !important;
            }

            .mla-drawer-scrim { left: 76px; }
            div[class*="st-key-mla_history_drawer"],
            div[class*="st-key-mla_wrongbook_drawer"] { left: 76px !important; }
            .mla-processing-modal {
                left: calc(76px + (100vw - 76px) / 2 - min(280px, 45vw));
                width: min(560px, 90vw);
            }
        }
        /* ---------- final Figma fidelity overrides ---------- */
        div[class*="st-key-mla_left_navigation"] {
            position: fixed !important;
            left: 0 !important;
            top: 0 !important;
            bottom: 0 !important;
            width: 236px !important;
            height: 100vh !important;
            padding: 20px !important;
            background: #2e291f !important;
            overflow: hidden !important;
        }

        div[class*="st-key-mla_left_navigation"] > div[data-testid="stVerticalBlock"] {
            gap: 18px !important;
        }

        div[class*="st-key-mla_left_navigation"] [data-testid="stElementContainer"] {
            width: 196px !important;
            margin: 0 !important;
        }

        .mla-nav-brand {
            width: 196px !important;
            height: 42px !important;
            padding: 4px 8px !important;
            background: #3d3629 !important;
            border: 1px solid #574d3d !important;
            border-radius: 12px !important;
        }

        .mla-nav-logo {
            position: relative !important;
            width: 34px !important;
            height: 34px !important;
            border-radius: 10px !important;
            background:
                linear-gradient(135deg, rgba(255,255,255,.18), rgba(255,255,255,0) 42%),
                #ba5c33 !important;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,.18);
            color: #241d15 !important;
            font-weight: 800 !important;
        }

        .mla-nav-logo span {
            position: relative;
            z-index: 1;
            font-size: 14px;
            line-height: 1;
        }

        .mla-nav-logo i {
            position: absolute;
            right: 7px;
            bottom: 7px;
            width: 7px;
            height: 2px;
            border-radius: 999px;
            background: rgba(38, 33, 26, .55);
            transform: rotate(-24deg);
        }

        .mla-nav-brand-copy strong {
            color: #fff4e6 !important;
            font-size: 14px !important;
            font-weight: 650 !important;
        }

        .mla-nav-brand-copy span {
            color: #c7bdab !important;
            font-size: 10px !important;
        }

        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_"] button,
        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_wrongbook"] button,
        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_history"] button {
            width: 196px !important;
            height: 44px !important;
            min-height: 44px !important;
            justify-content: flex-start !important;
            padding: 0 12px !important;
            border: 0 !important;
            border-radius: 12px !important;
            background: transparent !important;
            color: #dbd1bf !important;
            box-shadow: none !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }

        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_"] button *,
        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_wrongbook"] button *,
        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_history"] button * {
            color: inherit !important;
            opacity: 1 !important;
        }

        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {
            background: #54402e !important;
            color: #ffffff !important;
            font-weight: 700 !important;
        }

        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_"] button:hover,
        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_wrongbook"] button:hover,
        div[class*="st-key-mla_left_navigation"] div[class*="st-key-nav_history"] button:hover {
            background: #3d3629 !important;
            color: #ffffff !important;
        }

        .mla-daily-goal {
            left: 20px !important;
            bottom: 20px !important;
            width: 196px !important;
            height: 110px !important;
            background: #3d3629 !important;
            border-radius: 14px !important;
        }

        div[class*="st-key-mla_topbar"] {
            position: fixed !important;
            top: 0 !important;
            left: 236px !important;
            width: calc(100vw - 236px) !important;
            height: 76px !important;
            padding: 16px 24px !important;
            background: #fffef9 !important;
            border-bottom: 1px solid #dbd1ba !important;
            z-index: 2500 !important;
        }

        .mla-topbar-inner {
            width: 878px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .mla-top-title strong {
            font-size: 22px !important;
            line-height: 1.15 !important;
        }

        .mla-top-title span {
            font-size: 11px !important;
            color: #6e6657 !important;
        }

        .block-container {
            padding: 52px 24px 24px 260px !important;
            max-width: none !important;
        }

        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: 780px 356px !important;
            gap: 20px !important;
            align-items: start !important;
            justify-content: start !important;
            width: 1156px !important;
        }

        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1),
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1) > div,
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1) > div > div[data-testid="stVerticalBlock"] {
            width: 780px !important;
            flex: 0 0 780px !important;
            max-width: 780px !important;
        }

        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2),
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) > div,
        div[class*="st-key-mla_workspace_grid"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) > div > div[data-testid="stVerticalBlock"] {
            width: 356px !important;
            flex: 0 0 356px !important;
            max-width: 356px !important;
        }

        div[class*="st-key-mla_workspace_grid"] div[data-testid="stColumn"] > div > div[data-testid="stVerticalBlock"] {
            gap: 16px !important;
        }

        div[class*="st-key-mla_upload_card"],
        div[class*="st-key-mla_chat_card"] {
            width: 780px !important;
        }

        div[class*="st-key-mla_chat_card"] {
            height: calc(100vh - 124px) !important;
            min-height: 720px !important;
            max-height: none !important;
        }

        div[class*="st-key-mla_today_plan"],
        div[class*="st-key-mla_sources_card"],
        div[class*="st-key-mla_review_card"],
        div[class*="st-key-mla_study_tip"] {
            width: 356px !important;
        }

        div[class*="st-key-mla_upload_card"] [data-testid="stFileUploaderDropzone"] button::after {
            content: "选择文件" !important;
        }

        .mla-chat-welcome {
            height: auto !important;
            min-height: 116px !important;
            align-items: flex-start !important;
        }

        div[class*="st-key-mla_materials_drawer"] {
            position: fixed !important;
            left: 236px !important;
            top: 0 !important;
            bottom: 0 !important;
            z-index: 4100 !important;
            box-sizing: border-box !important;
            width: 390px !important;
            height: 100vh !important;
            padding: 20px !important;
            overflow-x: hidden !important;
            overflow-y: auto !important;
            background: var(--mla-paper) !important;
            box-shadow: 10px 0 32px rgba(26, 20, 13, .18) !important;
        }

        div[class*="st-key-mla_materials_drawer"] > div[data-testid="stVerticalBlock"] {
            gap: 14px !important;
        }

        div[class*="st-key-mla_materials_drawer"] [data-testid="stHorizontalBlock"]:first-child {
            display: grid !important;
            grid-template-columns: 270px 64px !important;
            gap: 10px !important;
            align-items: center !important;
        }

        div[class*="st-key-mla_materials_drawer"] [data-testid="stHorizontalBlock"]:first-child > [data-testid="column"] {
            width: auto !important;
            min-width: 0 !important;
            flex: none !important;
            padding: 0 !important;
        }

        div[class*="st-key-mla_materials_drawer"] button[kind="secondary"] {
            width: auto !important;
            height: 29px !important;
            min-height: 29px !important;
            padding: 0 8px !important;
            border: 0 !important;
            border-radius: 999px !important;
            background: var(--mla-bg) !important;
            color: var(--mla-muted) !important;
            font-size: 12px !important;
            font-weight: 500 !important;
        }

        .mla-materials-intro {
            box-sizing: border-box;
            width: 350px;
            padding: 14px;
            border: 1px solid var(--mla-border);
            border-radius: 14px;
            background: #ffffff;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .mla-materials-intro strong {
            color: var(--mla-ink);
            font-size: 15px;
            font-weight: 700;
        }

        .mla-materials-intro span {
            color: var(--mla-muted);
            font-size: 12px;
            line-height: 1.55;
        }

        div[class*="st-key-mla_materials_drawer"] [data-testid="stFileUploader"] {
            width: 350px !important;
        }

        div[class*="st-key-mla_materials_drawer"] [data-testid="stFileUploaderDropzone"] {
            min-height: 112px !important;
            border: 1px dashed var(--mla-border) !important;
            border-radius: 14px !important;
            background: var(--mla-bg) !important;
        }

        .mla-source-row.drawer {
            width: 350px !important;
            background: #ffffff !important;
        }

        .mla-material-stats {
            width: 350px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .mla-material-stats div {
            box-sizing: border-box;
            padding: 10px;
            border-radius: 12px;
            background: var(--mla-sage-soft);
            min-height: 74px;
        }

        .mla-material-stats span {
            display: block;
            color: var(--mla-muted);
            font-size: 12px;
            margin-bottom: 6px;
        }

        .mla-material-stats strong {
            display: block;
            color: var(--mla-ink);
            font-size: 20px;
            font-weight: 700;
            line-height: 1.2;
        }

        @media (max-width: 900px) {
            div[class*="st-key-mla_materials_drawer"] {
                left: 76px !important;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )



def render_section_note(text):
    st.markdown(
        f'<div class="mla-section-note">{escape(str(text))}</div>',
        unsafe_allow_html=True,
    )


def render_section_eyebrow(text):
    st.markdown(
        f'<div class="mla-section-eyebrow">{escape(str(text))}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_brand(product_name, product_chinese_name, session_id):
    st.markdown(
        f"""
        <div class="mla-nav-brand">
            <div class="mla-nav-logo">M</div>
            <div class="mla-nav-brand-copy">
                <strong>{escape(str(product_name))}</strong>
                <span>{escape(str(product_chinese_name))} · {escape(str(session_id))}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_grid(items):
    cards = []
    for item in items:
        cards.append(
            '<div class="mla-source-row">'
            f'<div class="mla-source-icon">{escape(str(item.get("label", "")))[:1]}</div>'
            '<div class="mla-source-copy">'
            f'<strong>{escape(str(item.get("value", "")))}</strong>'
            f'<span>{escape(str(item.get("note", "")))}</span>'
            '</div></div>'
        )
    st.markdown("".join(cards), unsafe_allow_html=True)


def open_workbench_layout():
    return None


def switch_to_workbench_rail():
    return None


def close_workbench_layout():
    return None


def open_panel_shell(extra_class=""):
    st.markdown(
        f'<section class="mla-save-box {escape(str(extra_class))}">',
        unsafe_allow_html=True,
    )


def close_panel_shell():
    st.markdown("</section>", unsafe_allow_html=True)


def open_chat_stage():
    return None


def close_chat_stage():
    return None


def open_surface(extra_class=""):
    open_panel_shell(extra_class)


def close_surface():
    close_panel_shell()


def render_assist_card(title, body):
    st.markdown(
        f"""
        <div class="mla-empty-note">
            <strong>{escape(str(title))}</strong><br>
            {escape(str(body))}
        </div>
        """,
        unsafe_allow_html=True,
    )
