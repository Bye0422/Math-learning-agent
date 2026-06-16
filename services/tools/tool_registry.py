from services.tools.calculator_tool import format_calculation_answer
from services.tools.log_query_tool import format_latest_log_answer


def run_calculator_tool(question, task_info=None, context=None):
    """
    计算器工具包装函数。
    """
    answer = format_calculation_answer(question)

    return {
        "success": True,
        "tool_name": "calculator_tool",
        "answer": answer,
        "metadata": {
            "task_type": "calculation",
        },
        "error": "",
    }


def run_log_query_tool(question, task_info=None, context=None):
    """
    日志查询工具包装函数。
    """
    answer = format_latest_log_answer()

    return {
        "success": True,
        "tool_name": "log_query_tool",
        "answer": answer,
        "metadata": {
            "task_type": "log_query",
        },
        "error": "",
    }


TOOL_REGISTRY = {
    "calculation": {
        "tool_name": "calculator_tool",
        "description": "用于执行确定性的数学表达式计算。",
        "runner": run_calculator_tool,
    },
    "log_query": {
        "tool_name": "log_query_tool",
        "description": "用于查询最近一次 Agent 运行日志。",
        "runner": run_log_query_tool,
    },
}


def is_tool_task(task_type):
    """
    判断当前 task_type 是否应该交给工具执行。
    """
    return task_type in TOOL_REGISTRY


def get_tool_info(task_type):
    """
    获取工具信息。
    """
    return TOOL_REGISTRY.get(task_type)


def list_available_tools():
    """
    返回当前已经注册的工具列表。
    """
    tools = []

    for task_type, tool_info in TOOL_REGISTRY.items():
        tools.append(
            {
                "task_type": task_type,
                "tool_name": tool_info["tool_name"],
                "description": tool_info["description"],
            }
        )

    return tools


def run_tool_by_task_type(task_type, question, task_info=None, context=None):
    """
    根据 task_type 调用对应工具。
    """
    tool_info = get_tool_info(task_type)

    if tool_info is None:
        return {
            "success": False,
            "tool_name": "",
            "answer": f"没有找到可执行工具：{task_type}",
            "metadata": {},
            "error": f"Unsupported tool task_type: {task_type}",
        }

    try:
        runner = tool_info["runner"]

        result = runner(
            question=question,
            task_info=task_info,
            context=context,
        )

        if not isinstance(result, dict):
            return {
                "success": False,
                "tool_name": tool_info["tool_name"],
                "answer": "工具返回结果格式错误。",
                "metadata": {},
                "error": "Tool result is not a dict.",
            }

        return result

    except Exception as e:
        return {
            "success": False,
            "tool_name": tool_info["tool_name"],
            "answer": f"工具调用失败：{e}",
            "metadata": {},
            "error": str(e),
        }