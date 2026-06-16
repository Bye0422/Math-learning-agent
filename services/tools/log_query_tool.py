import csv
from pathlib import Path

from config import LOG_DIR_NAME, LOG_FILE_NAME


def get_log_file_path():
    """
    获取日志文件路径。
    """
    return Path(LOG_DIR_NAME) / LOG_FILE_NAME


def read_latest_log():
    """
    读取最近一条 Agent 运行日志。
    """
    log_path = get_log_file_path()

    if not log_path.exists():
        return {
            "success": False,
            "error": f"没有找到日志文件：{log_path}",
            "data": None,
        }

    try:
        with log_path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

        if not rows:
            return {
                "success": False,
                "error": "日志文件存在，但目前没有日志记录。",
                "data": None,
            }

        return {
            "success": True,
            "error": "",
            "data": rows[-1],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None,
        }


def format_latest_log_answer():
    """
    把最近一条日志整理成适合展示的回答。
    """
    result = read_latest_log()

    if not result["success"]:
        return f"""日志查询失败：

{result["error"]}

说明：
当前日志查询工具会读取 logs/agent_logs.csv 中最近一条记录。"""

    row = result["data"]

    return f"""最近一次 Agent 运行日志：

用户问题：
{row.get("question", "")}

任务类型：
{row.get("task_type", "")}

是否需要 RAG：
{row.get("need_rag", "")}

实际检索问题：
{row.get("retrieval_question", "")}

Top K：
{row.get("top_k", "")}

命中的资料来源：
{row.get("retrieved_sources", "")}

答案长度：
{row.get("answer_length", "")}

格式是否合格：
{row.get("format_valid", "")}

缺失字段：
{row.get("missing_fields", "")}

是否触发自动修复：
{row.get("was_repaired", "")}

耗时：
{row.get("elapsed_seconds", "")} 秒

错误信息：
{row.get("error", "")}

说明：
以上内容由日志查询工具从 logs/agent_logs.csv 读取，不是大模型猜测。"""