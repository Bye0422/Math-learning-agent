import re


def safe_divide(a, b):
    if b == 0:
        return 0
    return a / b


def count_regex(pattern, text, flags=0):
    return len(re.findall(pattern, text, flags))


def get_non_space_text(text):
    return re.sub(r"\s+", "", text or "")


def calculate_garbled_ratio(text):
    """
    估算乱码比例。

    常见乱码包括：
    � □ ■ ◆ ◇ �
    以及一些不可见控制字符。
    """
    if not text:
        return 0

    non_space_text = get_non_space_text(text)

    if not non_space_text:
        return 0

    garbled_chars = re.findall(r"[�□■◆◇�]", text)

    control_chars = [
        ch for ch in text
        if ord(ch) < 32 and ch not in ["\n", "\r", "\t"]
    ]

    garbled_count = len(garbled_chars) + len(control_chars)

    return safe_divide(garbled_count, len(non_space_text))


def calculate_blank_line_ratio(text):
    """
    计算空行比例。
    """
    lines = text.splitlines()

    if not lines:
        return 1

    blank_lines = [line for line in lines if not line.strip()]

    return safe_divide(len(blank_lines), len(lines))


def calculate_content_density(text):
    """
    计算正文密度。
    过低说明空白、换行、无效字符可能比较多。
    """
    if not text:
        return 0

    non_space_len = len(get_non_space_text(text))

    return safe_divide(non_space_len, len(text))


def count_question_numbers(text):
    """
    统计题号数量。
    兼容：
    1.
    1、
    1．
    第 1 题
    （1）
    (1)
    """
    patterns = [
        r"(?m)^\s*\d+[\.、．]\s*",
        r"(?m)^\s*第\s*\d+\s*题",
        r"(?m)^\s*[（(]\d+[）)]",
    ]

    return sum(count_regex(pattern, text) for pattern in patterns)


def count_options(text):
    """
    统计选择题选项数量。
    兼容：
    A.
    A、
    A．
    （A）
    (A)
    """
    patterns = [
        r"(?m)^\s*[A-D][\.、．]\s*",
        r"(?m)^\s*[（(][A-D][）)]",
    ]

    return sum(count_regex(pattern, text) for pattern in patterns)


def count_math_tokens(text):
    """
    统计数学符号和 LaTeX 相关标记。
    """
    if not text:
        return 0

    math_patterns = [
        r"\$",
        r"\\frac",
        r"\\sum",
        r"\\int",
        r"\\sqrt",
        r"\\mathrm",
        r"\\alpha",
        r"\\beta",
        r"\\mu",
        r"\\sigma",
        r"\\theta",
        r"\\lambda",
        r"\\bar",
        r"\\hat",
        r"\\left",
        r"\\right",
        r"\\begin",
        r"\\end",
        r"[=＋+\-−×÷*/]",
        r"\d+\s*/\s*\d+",
    ]

    total = 0

    for pattern in math_patterns:
        total += count_regex(pattern, text)

    return total


def count_formula_lines(text):
    """
    统计疑似公式行。
    """
    lines = text.splitlines()
    count = 0

    math_keywords = [
        "$",
        "\\frac",
        "\\sum",
        "\\int",
        "\\sqrt",
        "\\mathrm",
        "=",
        "×",
        "÷",
    ]

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if any(keyword in stripped for keyword in math_keywords):
            count += 1

    return count


def detect_repeated_short_lines(text, min_repeat=3):
    """
    检测重复短行，通常是页眉、页脚、资料标题等。
    """
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    counter = {}

    for line in lines:
        if len(line) <= 40:
            counter[line] = counter.get(line, 0) + 1

    repeated = [
        line for line, count in counter.items()
        if count >= min_repeat
    ]

    return repeated


def score_pdf_parse_quality(metrics):
    """
    根据指标计算 0-100 分。
    """
    score = 100
    issues = []
    suggestions = []

    text_length = metrics["text_length"]
    garbled_ratio = metrics["garbled_ratio"]
    blank_line_ratio = metrics["blank_line_ratio"]
    content_density = metrics["content_density"]
    question_count = metrics["question_count"]
    option_count = metrics["option_count"]
    math_token_count = metrics["math_token_count"]
    formula_line_count = metrics["formula_line_count"]
    repeated_short_line_count = metrics["repeated_short_line_count"]

    if text_length < 200:
        score -= 45
        issues.append("解析文本过短，疑似 PDF 没有被正确解析。")
        suggestions.append("建议检查 PDF 是否为扫描版，或尝试拆分 PDF 后重新解析。")
    elif text_length < 800:
        score -= 25
        issues.append("解析文本偏短，可能存在内容缺失。")
        suggestions.append("建议对比原 PDF，检查题干和公式是否完整。")
    elif text_length < 1500:
        score -= 10
        issues.append("解析文本长度略短，建议人工抽查。")

    if garbled_ratio >= 0.1:
        score -= 40
        issues.append("乱码比例较高，可能存在字体编码或公式识别问题。")
        suggestions.append("建议使用 MinerU auto 模式，并确认项目路径和临时目录均为英文路径。")
    elif garbled_ratio >= 0.05:
        score -= 25
        issues.append("存在一定比例乱码，可能影响检索和回答。")
        suggestions.append("建议检查前几个 chunk，确认题干和公式是否可读。")
    elif garbled_ratio >= 0.02:
        score -= 10
        issues.append("存在少量疑似乱码。")

    if blank_line_ratio >= 0.7:
        score -= 20
        issues.append("空行比例过高，可能存在版面解析异常。")
        suggestions.append("建议查看 Markdown 输出，必要时减少每批解析页数。")
    elif blank_line_ratio >= 0.55:
        score -= 10
        issues.append("空行比例偏高。")

    if content_density < 0.25:
        score -= 20
        issues.append("正文密度较低，可能包含大量无效空白或断行。")
    elif content_density < 0.4:
        score -= 8
        issues.append("正文密度略低。")

    if question_count == 0:
        score -= 8
        issues.append("没有检测到明显题号。")
        suggestions.append("如果这是题目类 PDF，建议检查题号是否被解析丢失。")

    if option_count == 0:
        issues.append("没有检测到明显 A-D 选项。")
        suggestions.append("如果这是选择题资料，建议检查选项是否被解析完整。")

    if math_token_count == 0 and formula_line_count == 0:
        score -= 8
        issues.append("没有检测到明显数学公式或数学符号。")
        suggestions.append("如果这是数学公式 PDF，建议检查公式是否被 MinerU 正确识别。")
    elif math_token_count < 5 and formula_line_count < 2:
        score -= 4
        issues.append("检测到的数学公式较少，建议人工抽查公式完整性。")

    if repeated_short_line_count >= 5:
        score -= 5
        issues.append("检测到较多重复短行，可能存在页眉、页脚或页码残留。")
        suggestions.append("可通过 Markdown 清洗模块进一步过滤重复页眉页脚。")

    if score < 0:
        score = 0

    if score > 100:
        score = 100

    return score, issues, suggestions


def get_quality_level(score, good_score=80, medium_score=60):
    """
    根据分数返回质量等级。
    """
    if score >= good_score:
        return "good"

    if score >= medium_score:
        return "medium"

    return "poor"


def check_pdf_parse_quality(markdown_text):
    """
    PDF 解析质量检测主入口。
    """
    text = markdown_text or ""

    repeated_short_lines = detect_repeated_short_lines(text)

    metrics = {
        "text_length": len(text),
        "line_count": len(text.splitlines()),
        "garbled_ratio": round(calculate_garbled_ratio(text), 4),
        "blank_line_ratio": round(calculate_blank_line_ratio(text), 4),
        "content_density": round(calculate_content_density(text), 4),
        "question_count": count_question_numbers(text),
        "option_count": count_options(text),
        "math_token_count": count_math_tokens(text),
        "formula_line_count": count_formula_lines(text),
        "repeated_short_line_count": len(repeated_short_lines),
        "repeated_short_lines_sample": repeated_short_lines[:10],
    }

    score, issues, suggestions = score_pdf_parse_quality(metrics)

    level = get_quality_level(score)

    if not issues:
        issues = ["未发现明显解析质量问题。"]

    if not suggestions:
        suggestions = ["当前解析结果可直接进入 RAG 流程。"]

    return {
        "score": round(score, 2),
        "level": level,
        "metrics": metrics,
        "issues": issues,
        "suggestions": suggestions,
    }


def flatten_quality_for_metadata(quality_result):
    """
    将质量检测结果压平成 Chroma 可接受的 metadata。

    注意：
    Chroma metadata 不适合直接存 dict/list，
    所以这里只存字符串、数字、布尔值。
    """
    if not quality_result:
        return {}

    metrics = quality_result.get("metrics", {})

    return {
        "pdf_quality_score": quality_result.get("score", ""),
        "pdf_quality_level": quality_result.get("level", ""),
        "pdf_quality_issues": "；".join(quality_result.get("issues", [])),
        "pdf_quality_suggestions": "；".join(quality_result.get("suggestions", [])),
        "pdf_quality_text_length": metrics.get("text_length", ""),
        "pdf_quality_garbled_ratio": metrics.get("garbled_ratio", ""),
        "pdf_quality_blank_line_ratio": metrics.get("blank_line_ratio", ""),
        "pdf_quality_content_density": metrics.get("content_density", ""),
        "pdf_quality_question_count": metrics.get("question_count", ""),
        "pdf_quality_option_count": metrics.get("option_count", ""),
        "pdf_quality_math_token_count": metrics.get("math_token_count", ""),
        "pdf_quality_formula_line_count": metrics.get("formula_line_count", ""),
        "pdf_quality_repeated_short_line_count": metrics.get("repeated_short_line_count", ""),
    }