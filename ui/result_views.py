import streamlit as st


def render_pdf_quality_result(documents):
    """
    Show PDF parsing quality results.
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


def render_math_exam_items(items):
    """
    Show structured math question parsing results.
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


def render_stat_exam_items(items):
    return render_math_exam_items(items)


def render_wrong_cards(card_results):
    """
    Show generated wrong-question card images.
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
