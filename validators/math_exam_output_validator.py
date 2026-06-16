import json
import re


ALLOWED_TYPES = ["选择题", "判断题", "简答题", "填空题", "计算题"]

BANNED_TAGS = {
    "选择题",
    "判断题",
    "简答题",
    "填空题",
    "计算题",
    "简单",
    "困难",
    "难题",
    "容易",
}

BANNED_PHRASES = [
    "综上所述",
    "因此可知",
    "由此可见",
    "总而言之",
    "综上",
]


def extract_json_from_text(text):
    if not text:
        raise ValueError("模型输出为空。")

    text = text.strip()

    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except Exception:
        pass

    object_match = re.search(r"\{.*\}", text, re.S)
    array_match = re.search(r"\[.*\]", text, re.S)

    if object_match:
        return json.loads(object_match.group(0))

    if array_match:
        return json.loads(array_match.group(0))

    raise ValueError("没有找到可解析的 JSON。")


def normalize_items(data):
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            return data["items"]

        if all(key in data for key in ["analysis", "difficulty", "type", "tags"]):
            return [data]

    if isinstance(data, list):
        return data

    raise ValueError("JSON 格式不符合要求，必须是对象或数组。")


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


def normalize_type(value):
    value = str(value).strip()

    if value in ALLOWED_TYPES:
        return value

    return "计算题"


def clean_analysis(text):
    text = str(text or "").strip()

    # 统一中文句号
    text = text.replace("。", ".")

    for phrase in BANNED_PHRASES:
        text = text.replace(phrase, "")

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def clean_tags(tags):
    if isinstance(tags, str):
        raw_tags = re.split(r"[，,、;/；\s]+", tags)
    elif isinstance(tags, list):
        raw_tags = tags
    else:
        raw_tags = []

    cleaned = []

    for tag in raw_tags:
        tag = str(tag).strip()
        tag = tag.strip("，,。.;；、 ")

        if not tag:
            continue

        if tag in BANNED_TAGS:
            continue

        if tag not in cleaned:
            cleaned.append(tag)

    if not cleaned:
        cleaned = ["数学"]

    return cleaned[:4]


def validate_choice_start(analysis):
    return bool(re.match(r"^选 [A-D],", analysis))


def validate_blank_start(analysis):
    return bool(re.match(r"^填 .+?,", analysis))


def validate_item(item, index):
    errors = []

    if not isinstance(item, dict):
        return {
            "valid": False,
            "errors": [f"第 {index} 项不是 JSON 对象。"],
        }

    required_fields = ["analysis", "difficulty", "type", "tags"]

    for field in required_fields:
        if field not in item:
            errors.append(f"缺少字段：{field}")

    analysis = clean_analysis(item.get("analysis", ""))
    difficulty = normalize_difficulty(item.get("difficulty", 2))
    question_type = normalize_type(item.get("type", "计算题"))
    tags = clean_tags(item.get("tags", []))

    if not analysis:
        errors.append("analysis 不能为空。")

    if question_type not in ALLOWED_TYPES:
        errors.append("type 不在允许范围内。")

    if difficulty not in [1, 2, 3, 4, 5]:
        errors.append("difficulty 只能是 1、2、3、4、5。")

    if not isinstance(tags, list) or len(tags) < 1 or len(tags) > 4:
        errors.append("tags 必须是 1 到 4 个标签的列表。")

    if "。" in analysis:
        errors.append("analysis 中不能出现中文句号。")

    for phrase in BANNED_PHRASES:
        if phrase in analysis:
            errors.append(f"analysis 中不能出现空泛套话：{phrase}")

    if question_type == "选择题" and not validate_choice_start(analysis):
        errors.append("选择题 analysis 必须以“选 A,”这种格式开头。")

    if question_type == "填空题" and not validate_blank_start(analysis):
        errors.append("填空题 analysis 必须以“填 答案,”这种格式开头。")

    normalized_item = {
        "analysis": analysis,
        "difficulty": difficulty,
        "type": question_type,
        "tags": tags,
    }

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "item": normalized_item,
    }


def validate_math_exam_items(items):
    errors = []
    normalized_items = []

    if not isinstance(items, list):
        return {
            "valid": False,
            "errors": ["items 必须是列表。"],
            "items": [],
        }

    if not items:
        return {
            "valid": False,
            "errors": ["items 不能为空。"],
            "items": [],
        }

    for index, item in enumerate(items, start=1):
        result = validate_item(item, index)

        if result.get("item"):
            normalized_items.append(result["item"])

        if not result["valid"]:
            for error in result["errors"]:
                errors.append(f"第 {index} 题：{error}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "items": normalized_items,
    }


def parse_and_validate_math_exam_output(text):
    data = extract_json_from_text(text)
    items = normalize_items(data)
    return validate_math_exam_items(items)


def build_answer_text_from_items(items):
    return json.dumps(
        {
            "items": items,
        },
        ensure_ascii=False,
        indent=2,
    )