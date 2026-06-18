import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import (
    CARD_OUTPUT_DIR,
    CARD_IMAGE_WIDTH,
    CARD_MIN_IMAGE_HEIGHT,
    CARD_TITLE,
    CARD_FONT_PATHS,
)

try:
    from config import CARD_FOOTER
except Exception:
    CARD_FOOTER = "Math-learning-agent 数学学习助手"


CHINESE_NUM_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def ensure_card_dir():
    card_dir = Path(CARD_OUTPUT_DIR)
    card_dir.mkdir(parents=True, exist_ok=True)
    return card_dir


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_font(size=32, bold=False):
    """
    加载中文字体。
    Windows 优先使用微软雅黑 / 黑体 / 宋体。
    """
    for font_path in CARD_FONT_PATHS:
        path = Path(font_path)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except Exception:
                continue

    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except Exception:
        return ImageFont.load_default()


def text_width(draw, text, font):
    if not text:
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def text_height(draw, text, font):
    if not text:
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def wrap_text_by_pixel(draw, text, font, max_width):
    """
    按像素宽度自动换行。
    适合中文、英文、LaTeX 混排的普通展示。
    """
    if text is None:
        return [""]

    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    result_lines = []

    for raw_line in text.split("\n"):
        raw_line = raw_line.strip()

        if not raw_line:
            result_lines.append("")
            continue

        current = ""

        for char in raw_line:
            test = current + char

            if text_width(draw, test, font) <= max_width:
                current = test
            else:
                if current:
                    result_lines.append(current)
                current = char

        if current:
            result_lines.append(current)

    return result_lines


def draw_wrapped_text(
    draw,
    text,
    x,
    y,
    font,
    max_width,
    fill=(40, 40, 40),
    line_gap=12,
):
    lines = wrap_text_by_pixel(draw, text, font, max_width)
    current_y = y

    for line in lines:
        draw.text((x, current_y), line, font=font, fill=fill)
        current_y += text_height(draw, line if line else " ", font) + line_gap

    return current_y


def estimate_wrapped_height(draw, text, font, max_width, line_gap=12):
    lines = wrap_text_by_pixel(draw, text, font, max_width)
    height = 0

    for line in lines:
        height += text_height(draw, line if line else " ", font) + line_gap

    return height


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_difficulty(value):
    try:
        value = int(value)
    except Exception:
        value = 2

    if value < 1:
        value = 1
    if value > 5:
        value = 5

    return value


def difficulty_to_stars(value):
    value = normalize_difficulty(value)
    return "★" * value + "☆" * (5 - value)


def normalize_tags(tags):
    if isinstance(tags, list):
        cleaned = [str(tag).strip() for tag in tags if str(tag).strip()]
    elif isinstance(tags, str):
        cleaned = [
            tag.strip()
            for tag in re.split(r"[，,、;/；\s]+", tags)
            if tag.strip()
        ]
    else:
        cleaned = ["统计学"]

    if not cleaned:
        cleaned = ["统计学"]

    return cleaned[:4]


def build_card_id(question_text, item):
    raw = f"{question_text}|{item.get('analysis', '')}|{now_text()}|{uuid.uuid4().hex[:8]}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def extract_question_number(user_question):
    """
    从用户问题中提取题号。
    支持：第 2 题、第二题、2题。
    """
    text = user_question or ""

    match = re.search(r"第\s*(\d+)\s*题", text)
    if match:
        return int(match.group(1))

    match = re.search(r"第\s*([一二三四五六七八九十])\s*题", text)
    if match:
        return CHINESE_NUM_MAP.get(match.group(1))

    match = re.search(r"(\d+)\s*题", text)
    if match:
        return int(match.group(1))

    return None


def is_likely_full_question_text(text):
    """
    判断用户输入是否像完整题干。
    如果用户只是问“第 3 题怎么做”，就不算完整题干。
    """
    text = safe_text(text)

    if len(text) >= 80:
        return True

    question_keywords = [
        "已知",
        "设",
        "若",
        "求",
        "证明",
        "计算",
        "检验",
        "估计",
        "构造",
        "判断",
        "说明",
        "解释",
        "A.",
        "B.",
        "C.",
        "D.",
        "A、",
        "B、",
        "C、",
        "D、",
    ]

    hit_count = sum(1 for keyword in question_keywords if keyword in text)

    return hit_count >= 2 and len(text) >= 30


def normalize_question_text(text, max_chars=1200):
    text = safe_text(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if len(text) > max_chars:
        text = text[:max_chars] + "\n……题干过长，已截断……"

    return text


def extract_question_block_from_content(content, number):
    """
    从 chunk 内容中提取对应题号的题干块。
    这不是完美解析，但适合第一版 MVP。
    """
    if not content or not number:
        return ""

    text = content.replace("\r\n", "\n").replace("\r", "\n")

    current_patterns = [
        rf"(?m)^\s*{number}[\.、．]\s*",
        rf"(?m)^\s*第\s*{number}\s*题",
        rf"(?m)^\s*[（(]{number}[）)]",
    ]

    next_number = number + 1
    next_patterns = [
        rf"(?m)^\s*{next_number}[\.、．]\s*",
        rf"(?m)^\s*第\s*{next_number}\s*题",
        rf"(?m)^\s*[（(]{next_number}[）)]",
    ]

    start_positions = []

    for pattern in current_patterns:
        match = re.search(pattern, text)
        if match:
            start_positions.append(match.start())

    if not start_positions:
        return ""

    start = min(start_positions)
    rest = text[start:]

    end_positions = []

    for pattern in next_patterns:
        match = re.search(pattern, rest)
        if match and match.start() > 20:
            end_positions.append(match.start())

    if end_positions:
        end = min(end_positions)
        return rest[:end].strip()

    return rest[:1200].strip()


def infer_question_text_for_card(user_question, retrieved_docs_with_scores):
    """
    错题卡片中的题干来源。

    优先级：
    1. 如果用户输入本身就是完整题干，直接用用户输入。
    2. 如果用户问“第几题”，从检索片段里提取对应题号内容。
    3. 否则用 top1 chunk 的前一段作为题干候选。
    """
    user_question = safe_text(user_question)

    if is_likely_full_question_text(user_question):
        return normalize_question_text(user_question)

    question_number = extract_question_number(user_question)

    top_content = ""

    if retrieved_docs_with_scores:
        try:
            top_doc = retrieved_docs_with_scores[0][0]
            top_content = top_doc.page_content or ""
        except Exception:
            top_content = ""

    if question_number and top_content:
        block = extract_question_block_from_content(
            content=top_content,
            number=question_number,
        )

        if block:
            return normalize_question_text(block)

    if top_content:
        return normalize_question_text(top_content[:1000])

    return normalize_question_text(user_question)


def build_source_info(retrieved_docs_with_scores):
    """
    提取来源信息。
    """
    if not retrieved_docs_with_scores:
        return {
            "source_file": "",
            "source_location": "",
            "source_chunk_id": "",
        }

    try:
        doc = retrieved_docs_with_scores[0][0]
        metadata = doc.metadata or {}

        return {
            "source_file": metadata.get("source", ""),
            "source_location": metadata.get("location", ""),
            "source_chunk_id": metadata.get("chunk_id", ""),
        }
    except Exception:
        return {
            "source_file": "",
            "source_location": "",
            "source_chunk_id": "",
        }


def render_wrong_question_card(
    question_text,
    item,
    output_path=None,
):
    """
    将一道错题渲染成图片。

    输入 item：
    {
        "analysis": "...",
        "difficulty": 3,
        "type": "计算题",
        "tags": ["假设检验"]
    }
    """
    card_dir = ensure_card_dir()

    question_text = normalize_question_text(question_text)
    analysis = safe_text(item.get("analysis", ""))
    difficulty = normalize_difficulty(item.get("difficulty", 2))
    question_type = safe_text(item.get("type", "计算题"))
    tags = normalize_tags(item.get("tags", []))

    if output_path is None:
        card_id = build_card_id(question_text, item)
        output_path = card_dir / f"wrong_card_{card_id}.png"
    else:
        output_path = Path(output_path)

    width = CARD_IMAGE_WIDTH
    margin = 70
    content_width = width - margin * 2

    title_font = load_font(46)
    section_font = load_font(32)
    body_font = load_font(30)
    small_font = load_font(26)
    meta_font = load_font(28)

    temp_img = Image.new("RGB", (width, CARD_MIN_IMAGE_HEIGHT), (255, 255, 255))
    temp_draw = ImageDraw.Draw(temp_img)

    question_height = estimate_wrapped_height(
        temp_draw,
        question_text,
        body_font,
        content_width,
    )

    analysis_height = estimate_wrapped_height(
        temp_draw,
        analysis,
        body_font,
        content_width,
    )

    meta_height = 140
    header_height = 150
    section_gap = 38
    bottom_padding = 90

    final_height = max(
        CARD_MIN_IMAGE_HEIGHT,
        margin + header_height + question_height + section_gap + analysis_height + meta_height + bottom_padding,
    )

    img = Image.new("RGB", (width, final_height), (248, 250, 252))
    draw = ImageDraw.Draw(img)

    # 背景卡片
    card_x0 = 42
    card_y0 = 42
    card_x1 = width - 42
    card_y1 = final_height - 42

    draw.rounded_rectangle(
        (card_x0, card_y0, card_x1, card_y1),
        radius=32,
        fill=(255, 255, 255),
        outline=(220, 226, 235),
        width=2,
    )

    # 标题
    y = margin
    draw.text(
        (margin, y),
        CARD_TITLE,
        font=title_font,
        fill=(20, 39, 70),
    )

    draw.text(
        (margin, y + 60),
        f"生成时间：{now_text()}",
        font=small_font,
        fill=(110, 120, 135),
    )

    y += 135

    # 元信息条
    stars = difficulty_to_stars(difficulty)
    meta_text = f"难度：{stars}  |  题型：{question_type}  |  标签：{' / '.join(tags)}"

    draw.rounded_rectangle(
        (margin, y, width - margin, y + 62),
        radius=18,
        fill=(239, 246, 255),
        outline=(191, 219, 254),
        width=1,
    )

    draw.text(
        (margin + 24, y + 14),
        meta_text,
        font=meta_font,
        fill=(30, 64, 175),
    )

    y += 95

    # 题干
    draw.text(
        (margin, y),
        "题干",
        font=section_font,
        fill=(15, 23, 42),
    )

    y += 50

    y = draw_wrapped_text(
        draw=draw,
        text=question_text,
        x=margin,
        y=y,
        font=body_font,
        max_width=content_width,
        fill=(40, 40, 40),
        line_gap=14,
    )

    y += 38

    # 分割线
    draw.line(
        (margin, y, width - margin, y),
        fill=(226, 232, 240),
        width=2,
    )

    y += 38

    # 解析
    draw.text(
        (margin, y),
        "解析",
        font=section_font,
        fill=(15, 23, 42),
    )

    y += 50

    y = draw_wrapped_text(
        draw=draw,
        text=analysis,
        x=margin,
        y=y,
        font=body_font,
        max_width=content_width,
        fill=(40, 40, 40),
        line_gap=14,
    )

    # 页脚
    footer = CARD_FOOTER
    draw.text(
        (margin, final_height - 95),
        footer,
        font=small_font,
        fill=(140, 148, 160),
    )

    img.save(output_path, format="PNG")

    return str(output_path)


def render_cards_for_items(
    question_text,
    items,
):
    """
    批量渲染多个错题卡。
    """
    results = []

    for index, item in enumerate(items, start=1):
        image_path = render_wrong_question_card(
            question_text=question_text,
            item=item,
        )

        results.append(
            {
                "index": index,
                "question_text": question_text,
                "item": item,
                "image_path": image_path,
            }
        )

    return results
