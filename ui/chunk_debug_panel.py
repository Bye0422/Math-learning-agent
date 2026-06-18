import streamlit as st

from services.chunk_debug_service import (
    build_chunk_debug_rows,
    filter_chunk_debug_rows,
)
from services.correction_store_service import save_chunk_correction
from services.question_parser_service import parse_question_from_chunk
from ui.theme import render_section_note, render_status_grid


def render_chunk_debug_panel(chunks):
    with st.expander("Chunk 调试面板"):
        chunk_debug_rows = build_chunk_debug_rows(chunks)

        chunk_keyword = st.text_input(
            "搜索 chunk 内容、来源或位置",
            key="chunk_debug_keyword",
        )
        chunk_marker = st.text_input(
            "按题号过滤，例如：第1题、1.、(2)",
            key="chunk_debug_marker",
        )
        chunk_quality_filter = st.selectbox(
            "按质量过滤",
            options=["全部", "high_risk", "warning", "ok"],
            format_func=lambda value: {
                "全部": "全部",
                "high_risk": "高风险",
                "warning": "可疑",
                "ok": "正常",
            }.get(value, value),
            key="chunk_debug_quality_filter",
        )
        filtered_chunk_rows = filter_chunk_debug_rows(
            chunk_debug_rows,
            keyword=chunk_keyword,
            question_marker=chunk_marker,
        )

        if chunk_quality_filter != "全部":
            filtered_chunk_rows = [
                row
                for row in filtered_chunk_rows
                if row.get("quality_level") == chunk_quality_filter
            ]

        high_risk_count = sum(
            1 for row in chunk_debug_rows if row.get("quality_level") == "high_risk"
        )
        warning_count = sum(
            1 for row in chunk_debug_rows if row.get("quality_level") == "warning"
        )

        if high_risk_count or warning_count:
            st.warning(
                f"发现 {high_risk_count} 个高风险 chunk，"
                f"{warning_count} 个可疑 chunk。建议优先检查题干、选项和页脚。"
            )

        render_status_grid(
            [
                {
                    "label": "匹配 Chunk",
                    "value": len(filtered_chunk_rows),
                    "note": "当前筛选结果",
                },
                {
                    "label": "高风险",
                    "value": high_risk_count,
                    "note": "建议优先校正",
                },
                {
                    "label": "可疑",
                    "value": warning_count,
                    "note": "建议抽查",
                },
                {
                    "label": "总 Chunk",
                    "value": len(chunk_debug_rows),
                    "note": "当前文件会话",
                },
            ]
        )

        st.dataframe(
            filtered_chunk_rows[:100],
            use_container_width=True,
            hide_index=True,
        )

        selected_chunk = select_chunk(chunks, filtered_chunk_rows)

        if selected_chunk is None:
            return

        st.subheader("Chunk 原文")
        render_section_note("用于核对题干、选项、公式和页脚是否被正确录入。")
        st.write(selected_chunk.page_content)

        st.subheader("结构化题目预览")
        render_section_note("系统会尝试从 chunk 中抽取题号、题干、选项、答案和解析。")
        st.json(parse_question_from_chunk(selected_chunk))

        st.subheader("人工校正")
        render_section_note("保存后会记录到本地校正库；重新建立向量库后，校正文案会进入检索。")
        corrected_text = st.text_area(
            "修正后的 chunk 文本",
            value=selected_chunk.page_content,
            height=220,
            key=f"chunk_correction_text_{selected_chunk.metadata.get('chunk_id', '')}",
        )

        if st.button(
            "保存 chunk 校正",
            key=f"save_chunk_correction_{selected_chunk.metadata.get('chunk_id', '')}",
        ):
            save_chunk_correction(
                source=selected_chunk.metadata.get("source", ""),
                chunk_id=selected_chunk.metadata.get("chunk_id", ""),
                corrected_text=corrected_text,
            )
            selected_chunk.page_content = corrected_text
            selected_chunk.metadata["chunk_corrected"] = True
            st.success("chunk 校正已保存。重新建立向量库后，校正文案会进入检索。")


def select_chunk(chunks, filtered_chunk_rows):
    chunk_options = [
        f"Chunk {row.get('chunk_id')} | {row.get('question_marker') or '普通片段'} | {row.get('preview')[:40]}"
        for row in filtered_chunk_rows[:100]
    ]
    chunk_option_to_id = {
        option: filtered_chunk_rows[index].get("chunk_id")
        for index, option in enumerate(chunk_options)
    }

    selected_chunk_option = st.selectbox(
        "查看 chunk 原文",
        options=[""] + chunk_options,
        format_func=lambda value: "请选择 chunk" if value == "" else value,
        key="chunk_debug_selected_option",
    )

    if not selected_chunk_option:
        return None

    selected_chunk_id = chunk_option_to_id.get(selected_chunk_option)

    for chunk in chunks:
        if chunk.metadata.get("chunk_id") == selected_chunk_id:
            return chunk

    return None
