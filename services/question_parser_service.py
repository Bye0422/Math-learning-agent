import re


QUESTION_NUMBER_PATTERN = re.compile(
    r"^\s*(?:第\s*)?(?P<number>\d+|[一二两三四五六七八九十]+|[①②③④⑤⑥⑦⑧⑨⑩])\s*(?:题|小题|问|[\.．、])?"
)
OPTION_LINE_PATTERN = re.compile(r"^\s*(?:[（(]?(?P<label>[A-D])[）)]?|(?P<label2>[A-D]))[\.、．]?\s*(?P<text>.+)$")


def parse_question_from_chunk(chunk):
    metadata = getattr(chunk, "metadata", None) or {}
    text = (getattr(chunk, "page_content", "") or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    question_number = extract_question_number(metadata, text)
    options = {}
    question_lines = []
    analysis_lines = []
    answer = ""
    mode = "question"

    for line in lines:
        option_match = OPTION_LINE_PATTERN.match(line)

        if option_match:
            label = option_match.group("label") or option_match.group("label2")
            options[label] = option_match.group("text").strip()
            continue

        if re.match(r"^(答案|参考答案)[:：]?", line):
            answer = re.sub(r"^(答案|参考答案)[:：]?", "", line).strip()
            mode = "analysis"
            continue

        if re.match(r"^(解析|解答|分析)[:：]?", line):
            analysis_text = re.sub(r"^(解析|解答|分析)[:：]?", "", line).strip()
            if analysis_text:
                analysis_lines.append(analysis_text)
            mode = "analysis"
            continue

        if mode == "analysis":
            analysis_lines.append(line)
        else:
            question_lines.append(line)

    question_text = "\n".join(question_lines).strip()
    question_text = strip_leading_question_marker(question_text)

    return {
        "question_number": question_number,
        "section": infer_section(text),
        "question_text": question_text,
        "options": options,
        "answer": answer,
        "analysis": "\n".join(analysis_lines).strip(),
        "source": metadata.get("source", ""),
        "location": metadata.get("location", ""),
        "chunk_id": metadata.get("chunk_id", ""),
        "question_marker": metadata.get("question_marker", ""),
        "quality_level": metadata.get("chunk_quality_level", ""),
        "quality_issues": metadata.get("chunk_quality_issues", []),
    }


def extract_question_number(metadata, text):
    marker = str(metadata.get("question_marker", "") or "").strip()
    source = marker or text
    match = QUESTION_NUMBER_PATTERN.match(source)

    if not match:
        return ""

    return match.group("number")


def strip_leading_question_marker(text):
    return QUESTION_NUMBER_PATTERN.sub("", text or "", count=1).strip()


def infer_section(text):
    if re.search(r"选择题|单选|多选", text):
        return "选择题"

    if re.search(r"填空题", text):
        return "填空题"

    if re.search(r"判断题", text):
        return "判断题"

    if re.search(r"简答题|简述", text):
        return "简答题"

    if re.search(r"计算题|求|证明", text):
        return "计算题"

    return ""


def parse_questions_from_chunks(chunks):
    questions = []

    for chunk in chunks or []:
        metadata = getattr(chunk, "metadata", None) or {}

        if not metadata.get("question_chunk"):
            continue

        parsed = parse_question_from_chunk(chunk)

        if parsed["question_text"] or parsed["options"]:
            questions.append(parsed)

    return questions
