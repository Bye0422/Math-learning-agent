import ast
import math
import re


ALLOWED_FUNCTIONS = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "round": round,
}

ALLOWED_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Num,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
    ast.Call,
    ast.Name,
    ast.Load,
)


def normalize_expression(text):
    """
    将用户输入中的常见数学符号转成 Python 可计算表达式。
    """
    expression = text.strip()

    expression = expression.replace("×", "*")
    expression = expression.replace("÷", "/")
    expression = expression.replace("^", "**")
    expression = expression.replace("（", "(")
    expression = expression.replace("）", ")")
    expression = expression.replace("，", ",")
    expression = expression.replace("＝", "=")

    remove_words = [
        "请帮我计算",
        "帮我计算",
        "请计算",
        "计算一下",
        "算一下",
        "计算",
        "结果是多少",
        "等于多少",
        "是多少",
        "请问",
    ]

    for word in remove_words:
        expression = expression.replace(word, "")

    if "=" in expression:
        expression = expression.split("=")[-1]

    return expression.strip()


def extract_expression_from_question(question):
    """
    从用户问题中提取计算表达式。
    """
    expression = normalize_expression(question)

    matches = re.findall(
        r"[0-9A-Za-z_\.\+\-\*/\%\(\),\s]+",
        expression,
    )

    if not matches:
        return expression

    expression = max(matches, key=len).strip()
    return expression


def validate_ast(node):
    """
    校验 AST，避免执行危险代码。
    """
    if not isinstance(node, ALLOWED_AST_NODES):
        raise ValueError(f"不允许的表达式类型：{type(node).__name__}")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("只允许调用白名单数学函数。")

        if node.func.id not in ALLOWED_FUNCTIONS:
            raise ValueError(f"不允许调用函数：{node.func.id}")

    if isinstance(node, ast.Name):
        if node.id not in ALLOWED_FUNCTIONS and node.id not in ALLOWED_CONSTANTS:
            raise ValueError(f"不允许使用变量：{node.id}")

    for child in ast.iter_child_nodes(node):
        validate_ast(child)


def safe_calculate(expression):
    """
    安全计算数学表达式。
    """
    expression = expression.strip()

    if not expression:
        raise ValueError("没有识别到可计算的表达式。")

    tree = ast.parse(expression, mode="eval")
    validate_ast(tree)

    safe_globals = {
        "__builtins__": {},
    }

    safe_locals = {}
    safe_locals.update(ALLOWED_FUNCTIONS)
    safe_locals.update(ALLOWED_CONSTANTS)

    result = eval(
        compile(tree, filename="<calculator>", mode="eval"),
        safe_globals,
        safe_locals,
    )

    return result


def calculate_from_question(question):
    """
    计算器工具入口。
    """
    expression = extract_expression_from_question(question)

    try:
        result = safe_calculate(expression)

        return {
            "success": True,
            "expression": expression,
            "result": result,
            "error": "",
        }

    except Exception as e:
        return {
            "success": False,
            "expression": expression,
            "result": None,
            "error": str(e),
        }


def format_calculation_answer(question):
    """
    返回适合页面展示的计算器工具答案。
    """
    tool_result = calculate_from_question(question)

    if tool_result["success"]:
        return f"""计算结果：
{tool_result["expression"]} = {tool_result["result"]}

说明：
该结果由 Python 计算器工具完成，不是大模型心算。"""

    return f"""计算失败：
{tool_result["error"]}

识别到的表达式：
{tool_result["expression"]}

说明：
当前计算器工具只支持基础数学表达式，例如 +、-、*、/、**、sqrt、log、sin、cos、tan 等。"""