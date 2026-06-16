import json
import re

from services.llm_service import get_chat_llm
from validators.math_exam_output_validator import (
    parse_and_validate_math_exam_output,
    validate_math_exam_items,
)


ALLOWED_TYPES = ["选择题", "判断题", "简答题", "填空题", "计算题"]


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_tags_from_text(tags_text):
    """
    将用户输入的标签字符串转为列表。
    支持：
    导数, 乘积求导
    导数，乘积求导
    导数 / 乘积求导
    """
    if isinstance(tags_text, list):
        tags = [str(tag).strip() for tag in tags_text if str(tag).strip()]
    else:
        tags = [
            tag.strip()
            for tag in re.split(r"[，,、;/；\s]+", str(tags_text))
            if tag.strip()
        ]

    if not tags:
        tags = ["数学"]

    return tags[:4]


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
    value = safe_text(value)

    if value in ALLOWED_TYPES:
        return value

    return "计算题"


def build_item_from_user_edit(
    analysis,
    difficulty,
    question_type,
    tags_text,
):
    """
    根据用户手动编辑内容生成标准 item。
    """
    item = {
        "analysis": safe_text(analysis),
        "difficulty": normalize_difficulty(difficulty),
        "type": normalize_type(question_type),
        "tags": normalize_tags_from_text(tags_text),
    }

    result = validate_math_exam_items([item])

    if result.get("items"):
        return result["items"][0]

    return item


def build_llm_edit_prompt(
    question_text,
    current_item,
    edit_instruction,
):
    """
    构造让 LLM 修改当前错题卡的 prompt。
    """
    return f"""
你是一个数学错题卡编辑助手。

你需要根据用户的修改要求，修改当前错题卡内容。

重要要求：

1. 只能修改题干、解析、难度、题型、标签中用户要求修改的部分。
2. 如果用户没有要求修改某一项，尽量保留原内容。
3. 题干中的具体数字、条件、选项不能胡编。
4. 解析必须完整、清楚。
5. 所有数学公式、符号、数字结果必须使用 LaTeX。
6. analysis 中不要出现中文句号“。”，统一使用英文句号“.”。
7. 不要出现“综上所述”“因此可知”“由此可见”“总而言之”等空泛套话。
8. difficulty 只能是 1、2、3、4、5。
9. type 只能是：选择题、判断题、简答题、填空题、计算题。
10. tags 必须是列表，至少 1 个，最多 4 个。
11. 只输出 JSON，不要输出 Markdown，不要解释。

输出格式必须是：

{{
  "question_text": "题干",
  "items": [
    {{
      "analysis": "解析",
      "difficulty": 2,
      "type": "计算题",
      "tags": ["知识点"]
    }}
  ]
}}

当前题干：
{question_text}

当前错题卡 item：
{json.dumps(current_item, ensure_ascii=False, indent=2)}

用户修改要求：
{edit_instruction}

请输出修改后的 JSON。
"""


def call_llm(prompt, temperature=0.2):
    try:
        llm = get_chat_llm(temperature=temperature)
    except TypeError:
        llm = get_chat_llm()

    response = llm.invoke(prompt)

    if hasattr(response, "content"):
        return response.content

    return str(response)


def extract_json_from_text(text):
    text = safe_text(text)

    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.S)

    if match:
        return json.loads(match.group(0))

    raise ValueError("LLM 修改结果不是合法 JSON。")


def edit_card_with_llm(
    question_text,
    current_item,
    edit_instruction,
):
    """
    让 LLM 根据用户要求修改当前错题卡。
    返回：
    {
        "question_text": "...",
        "items": [...]
    }
    """
    prompt = build_llm_edit_prompt(
        question_text=question_text,
        current_item=current_item,
        edit_instruction=edit_instruction,
    )

    raw_output = call_llm(prompt, temperature=0.2)
    data = extract_json_from_text(raw_output)

    new_question_text = safe_text(data.get("question_text", question_text))
    items = data.get("items", [])

    validation_result = parse_and_validate_math_exam_output(
        json.dumps(
            {
                "items": items,
            },
            ensure_ascii=False,
        )
    )

    if not validation_result.get("items"):
        raise ValueError("LLM 修改后没有得到有效 items。")

    return {
        "question_text": new_question_text,
        "items": validation_result["items"],
        "validation_result": validation_result,
        "raw_output": raw_output,
    }