import re

from services.question_chunker import find_question_markers


OPTION_PATTERN = re.compile(r"(?m)^\s*(?:[A-D][\.、．]|[（(][A-D][）)])")
GLUED_OPTION_PATTERN = re.compile(r"[A-D][\.、．][^\n]{4,}[B-D][\.、．]")
SOURCE_URL_PATTERN = re.compile(r"https?://\S+")


def inspect_chunk_quality(chunk):
    metadata = getattr(chunk, "metadata", None) or {}
    text = (getattr(chunk, "page_content", "") or "").strip()
    issues = []

    markers = find_question_markers(text)
    option_count = len(OPTION_PATTERN.findall(text))

    if metadata.get("question_chunk") and not metadata.get("question_marker"):
        issues.append("题块缺少题号")

    if metadata.get("question_chunk") and len(text) < 20:
        issues.append("题干过短")

    if len(markers) >= 2 and metadata.get("question_chunk"):
        issues.append("一个 chunk 内疑似包含多道题")

    if GLUED_OPTION_PATTERN.search(text):
        issues.append("选项疑似粘连")

    if SOURCE_URL_PATTERN.search(text):
        issues.append("包含来源 URL 或页脚")

    if metadata.get("question_chunk") and re.search(r"选择题|单选|多选", text) and option_count == 0:
        issues.append("选择题缺少可识别选项")

    if re.search(r"[�□■◆◇]", text):
        issues.append("存在疑似乱码")

    if text.startswith("解析") or text.startswith("答案"):
        issues.append("chunk 可能从答案或解析开始")

    level = "ok"

    if issues:
        level = "warning"

    if any(issue in issues for issue in ["一个 chunk 内疑似包含多道题", "选项疑似粘连", "存在疑似乱码"]):
        level = "high_risk"

    return {
        "chunk_quality_level": level,
        "chunk_quality_issues": issues,
        "chunk_question_marker_count": len(markers),
        "chunk_option_count": option_count,
    }
