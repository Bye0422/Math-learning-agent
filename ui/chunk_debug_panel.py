import streamlit as st

from services.chunk_debug_service import (
    build_chunk_debug_rows,
    filter_chunk_debug_rows,
)
from services.correction_store_service import save_chunk_correction
from ui.theme import render_section_note


def render_chunk_debug_panel(chunks):
    chunk_debug_rows = build_chunk_debug_rows(chunks)

    if not chunk_debug_rows:
        st.info("上传资料后，这里会显示可校正的文本片段。")
        return

    col1, col2 = st.columns([1.1, 0.9])

    with col1:
        chunk_keyword = st.text_input(
            "搜索片段内容",
            key="chunk_debug_keyword",
            placeholder="输入题干关键词、页码或文件名",
        )

    with col2:
        chunk_marker = st.text_input(
            "按题号定位",
            key="chunk_debug_marker",
            placeholder="例如：第 3 题、3、3)",
        )

    filtered_chunk_rows = filter_chunk_debug_rows(
        chunk_debug_rows,
        keyword=chunk_keyword,
        question_marker=chunk_marker,
    )

    selected_chunk = select_chunk(chunks, filtered_chunk_rows)

    if selected_chunk is None:
        st.caption(f"已找到 {len(filtered_chunk_rows)} 个片段。选择一个片段后可直接修改文本。")
        return

    metadata = selected_chunk.metadata or {}
    st.markdown("**原始片段**")
    render_section_note("检查题干、选项、公式和页脚是否被正确读取。")
    st.write(selected_chunk.page_content)

    st.markdown("**修改后的片段**")
    corrected_text = st.text_area(
        "修改 chunk 文本",
        value=selected_chunk.page_content,
        height=220,
        label_visibility="collapsed",
        key=f"chunk_correction_text_{metadata.get('chunk_id', '')}",
    )

    if st.button(
        "保存 chunk 修改",
        key=f"save_chunk_correction_{metadata.get('chunk_id', '')}",
    ):
        save_chunk_correction(
            source=metadata.get("source", ""),
            chunk_id=metadata.get("chunk_id", ""),
            corrected_text=corrected_text,
        )
        selected_chunk.page_content = corrected_text
        selected_chunk.metadata["chunk_corrected"] = True
        st.success("已保存。重新上传或重建资料后，修改内容会进入后续问答。")


def select_chunk(chunks, filtered_chunk_rows):
    chunk_options = [
        f"Chunk {row.get('chunk_id')} | {row.get('question_marker') or '普通片段'} | {row.get('preview')[:48]}"
        for row in filtered_chunk_rows[:100]
    ]
    chunk_option_to_id = {
        option: filtered_chunk_rows[index].get("chunk_id")
        for index, option in enumerate(chunk_options)
    }

    selected_chunk_option = st.selectbox(
        "选择要修改的 chunk",
        options=[""] + chunk_options,
        format_func=lambda value: "请选择一个片段" if value == "" else value,
        key="chunk_debug_selected_option",
    )

    if not selected_chunk_option:
        return None

    selected_chunk_id = chunk_option_to_id.get(selected_chunk_option)

    for chunk in chunks:
        if chunk.metadata.get("chunk_id") == selected_chunk_id:
            return chunk

    return None
