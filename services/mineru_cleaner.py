import re
from collections import Counter


def is_page_number_line(line: str) -> bool:
    """
    判断一行是否像页码。
    """
    text = line.strip()

    if not text:
        return False

    patterns = [
        r"^\d+$",
        r"^-+\s*\d+\s*-+$",
        r"^第\s*\d+\s*页$",
        r"^Page\s*\d+$",
        r"^page\s*\d+$",
        r"^\d+\s*/\s*\d+$",
        r"^第\s*\d+\s*页\s*/\s*共\s*\d+\s*页$",
    ]

    return any(re.match(pattern, text) for pattern in patterns)


def is_likely_question_or_option(line: str) -> bool:
    """
    判断是否像题号或选项，避免误删。
    """
    text = line.strip()

    question_patterns = [
        r"^\d+[\.、．]\s*",
        r"^第\s*\d+\s*题",
        r"^\(\d+\)",
        r"^（\d+）",
        r"^[A-D][\.、．]\s*",
        r"^（[A-D]）",
        r"^\([A-D]\)",
    ]

    return any(re.match(pattern, text) for pattern in question_patterns)


def is_likely_math_line(line: str) -> bool:
    """
    判断是否像数学公式，避免误删。
    """
    text = line.strip()

    math_tokens = [
        "$",
        "\\",
        "=",
        "+",
        "-",
        "×",
        "÷",
        "\\frac",
        "\\sum",
        "\\int",
        "\\sqrt",
        "\\mathrm",
        "\\alpha",
        "\\beta",
        "\\mu",
        "\\sigma",
        "\\theta",
    ]

    return any(token in text for token in math_tokens)


def remove_page_number_lines(markdown_text: str) -> str:
    """
    删除明显页码行。
    """
    lines = markdown_text.splitlines()
    cleaned_lines = []

    for line in lines:
        if is_page_number_line(line):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def remove_repeated_short_lines(markdown_text: str, min_repeat: int = 3) -> str:
    """
    删除重复出现的短行，通常是页眉、页脚、资料标题等。
    """
    lines = markdown_text.splitlines()

    normalized_lines = [
        line.strip()
        for line in lines
        if line.strip()
    ]

    counter = Counter(normalized_lines)
    repeated_noise = set()

    for text, count in counter.items():
        if count < min_repeat:
            continue

        if len(text) > 40:
            continue

        if is_likely_question_or_option(text):
            continue

        if is_likely_math_line(text):
            continue

        if re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", text):
            repeated_noise.add(text)

    cleaned_lines = []

    for line in lines:
        text = line.strip()

        if text in repeated_noise:
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def normalize_blank_lines(markdown_text: str) -> str:
    """
    合并过多空行。
    """
    text = re.sub(r"\n{4,}", "\n\n\n", markdown_text)
    return text.strip()


def clean_mineru_markdown(markdown_text: str) -> str:
    """
    MinerU Markdown 清洗入口。
    """
    text = markdown_text

    text = remove_page_number_lines(text)
    text = remove_repeated_short_lines(text, min_repeat=3)
    text = normalize_blank_lines(text)

    return text