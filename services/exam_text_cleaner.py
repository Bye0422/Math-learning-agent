import re


URL_PATTERN = re.compile(r"https?://\S+")
OPTION_MARKER_PATTERN = re.compile(r"([^\n])([A-D])([\.、．])")
QUESTION_INLINE_PATTERN = re.compile(
    r"(?<!^)(?<!\n)(?P<marker>(?:第\s*\d+\s*(?:题|小题|问))|(?:\d+\s*[\.．、]))"
)


def normalize_exam_text(text):
    """
    Normalize exam-like text before question chunking.

    This is intentionally conservative: it fixes common OCR/MinerU layout issues
    without trying to rewrite math formulas or infer missing content.
    """
    if not text:
        return ""

    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = remove_source_urls(normalized)
    normalized = transform_outside_latex(
        normalized,
        [
            normalize_question_markers,
            normalize_option_markers,
            normalize_choice_parentheses,
            normalize_excess_spaces,
        ],
    )
    normalized = normalize_blank_lines(normalized)

    return normalized.strip()


def transform_outside_latex(text, transforms):
    parts = re.split(r"(\$[^$]*\$)", text)
    cleaned_parts = []

    for part in parts:
        if part.startswith("$") and part.endswith("$"):
            cleaned_parts.append(part)
            continue

        for transform in transforms:
            part = transform(part)

        cleaned_parts.append(part)

    return "".join(cleaned_parts)


def remove_source_urls(text):
    lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if URL_PATTERN.fullmatch(stripped):
            continue

        lines.append(URL_PATTERN.sub("", line).rstrip())

    return "\n".join(lines)


def normalize_question_markers(text):
    return QUESTION_INLINE_PATTERN.sub(r"\n\g<marker>", text)


def normalize_option_markers(text):
    return OPTION_MARKER_PATTERN.sub(r"\1\n\2\3", text)


def normalize_choice_parentheses(text):
    return re.sub(
        r"(?<!^)(?<!\n)([（(][A-D][）)])",
        r"\n\1",
        text,
    )


def normalize_excess_spaces(text):
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"([，。；：、])[ \t]+", r"\1", text)
    return text


def normalize_blank_lines(text):
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text
