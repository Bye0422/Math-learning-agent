from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent


def read_prompt_file(file_name):
    return (PROMPT_DIR / file_name).read_text(encoding="utf-8")


def build_math_exam_answer_prompt(
    question,
    task_type,
    question_type,
    context_text,
    sources_text,
    chat_history_text="",
):
    base_prompt = read_prompt_file("KAFANG_MODEL_PROMPT.md")

    return f"""
{base_prompt}

当前任务类型：
{task_type}

初步题型判断：
{question_type}

历史对话：
{chat_history_text}

用户问题：
{question}

资料片段：
{context_text}

资料来源：
{sources_text}
""".strip()


def build_math_exam_repair_prompt(
    raw_output,
    question,
    task_type,
    question_type,
    validation_errors=None,
):
    validation_prompt = read_prompt_file("KAFANG_VALIDATION_PROMPT.md")

    return f"""
{validation_prompt}

用户问题：
{question}

任务类型：
{task_type}

初步题型判断：
{question_type}

校验提示：
{validation_errors or "请按验证提示词进行完整边界检查和格式重写。"}

第一轮解析草稿：
{raw_output}
""".strip()
