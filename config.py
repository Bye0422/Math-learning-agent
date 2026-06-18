import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def env_str(name, default):
    return os.getenv(name, str(default))


def env_path(name, default):
    value = Path(os.getenv(name, str(default))).expanduser()

    if value.is_absolute():
        return str(value)

    return str(PROJECT_ROOT / value)


def env_bool(name, default):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


# =========================
# 页面配置
# =========================

APP_PAGE_TITLE = "Math-learning-agent 数学学习助手"
APP_TITLE = "Math-learning-agent 数学学习助手"


# =========================
# 支持的文件类型
# =========================

SUPPORTED_FILE_TYPES = ["pdf", "docx", "txt", "png", "jpg", "jpeg", "webp"]


# =========================
# 文本切分参数
# =========================

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
CHUNK_SEPARATORS = ["\n\n", "\n", "。", "，", " ", ""]
ENABLE_QUESTION_CHUNKING = env_bool("ENABLE_QUESTION_CHUNKING", True)
QUESTION_CHUNK_MIN_MARKERS = env_int("QUESTION_CHUNK_MIN_MARKERS", 2)
QUESTION_CHUNK_MAX_CHARS = env_int("QUESTION_CHUNK_MAX_CHARS", 2500)


# =========================
# Embedding 参数
# =========================

EMBEDDING_BATCH_SIZE = 10
CHECK_EMBEDDING_CTX_LENGTH = False
TIKTOKEN_ENABLED = False


# =========================
# 检索参数
# =========================

DEFAULT_TOP_K = 3
SUMMARY_TOP_K = 5
EXTRACT_POINTS_TOP_K = 5


# =========================
# 模型温度参数
# =========================

ROUTER_TEMPERATURE = 0.1
REWRITE_TEMPERATURE = 0.1
ANSWER_TEMPERATURE = 0.2
REPAIR_TEMPERATURE = 0.1
DIRECT_TEMPERATURE = 0.2
OCR_TEMPERATURE = 0.1


# =========================
# 多轮对话参数
# =========================

MAX_HISTORY_MESSAGES = 6


# =========================
# 日志参数
# =========================

LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "agent_logs.csv"


# =========================
# 导出参数
# =========================

EXPORT_FILE_PREFIX = "rag_agent_export"
EXPORT_TITLE = "Math-learning-agent 数学学习助手问答导出"

# =========================
# 混合检索参数
# =========================

HYBRID_VECTOR_TOP_N = 8
HYBRID_RULE_TOP_N = 8

# 如果用户问题里有“第几题 / 选择题第几题”，规则检索权重更高
HYBRID_VECTOR_WEIGHT_WITH_REF = 0.35
HYBRID_RULE_WEIGHT_WITH_REF = 0.65

# 普通问题仍然以向量检索为主
HYBRID_VECTOR_WEIGHT_NORMAL = 0.75
HYBRID_RULE_WEIGHT_NORMAL = 0.25


# =========================
# 向量库参数
# =========================

VECTOR_COLLECTION_PREFIX = "rag_docs"
ENABLE_VECTOR_CACHE = env_bool("ENABLE_VECTOR_CACHE", True)
VECTOR_CACHE_DIR_NAME = env_path(
    "VECTOR_CACHE_DIR_NAME",
    PROJECT_ROOT / "cache" / "vector_store",
)


# =========================
# MinerU PDF 解析参数
# =========================

USE_MINERU_FOR_PDF = env_bool("USE_MINERU_FOR_PDF", True)

# 默认使用项目内虚拟环境的 MinerU 命令，可通过 .env 覆盖
MINERU_CMD = env_path(
    "MINERU_CMD",
    PROJECT_ROOT / ".venv" / "Scripts" / "mineru.exe",
)

# MinerU 后端
MINERU_BACKEND = env_str("MINERU_BACKEND", "pipeline")

# 数学公式 PDF 优先 auto，不默认 ocr
MINERU_METHOD = env_str("MINERU_METHOD", "auto")

# 中文真题、中文讲义用 ch
MINERU_LANG = env_str("MINERU_LANG", "ch")

# 公式 PDF 解析较慢，给足时间
MINERU_TIMEOUT_SECONDS = env_int("MINERU_TIMEOUT_SECONDS", 1800)

# MinerU 输入输出临时目录，建议使用英文路径
MINERU_TEMP_DIR_NAME = env_path(
    "MINERU_TEMP_DIR_NAME",
    PROJECT_ROOT / "mineru_runtime",
)

# 大 PDF 自动分批解析
MINERU_ENABLE_PAGE_BATCH = env_bool("MINERU_ENABLE_PAGE_BATCH", True)

# 数学公式 PDF 建议 5 页一批，更稳
MINERU_PAGE_BATCH_SIZE = env_int("MINERU_PAGE_BATCH_SIZE", 5)

# 你的 PDF 主要不是扫描版，所以先不自动转 OCR
MINERU_TRY_OCR_WHEN_AUTO_FAILS = env_bool("MINERU_TRY_OCR_WHEN_AUTO_FAILS", False)

# =========================
# MinerU 缓存配置
# =========================

MINERU_ENABLE_CACHE = env_bool("MINERU_ENABLE_CACHE", True)

MINERU_CACHE_DIR_NAME = env_path(
    "MINERU_CACHE_DIR_NAME",
    PROJECT_ROOT / "cache" / "mineru_markdown",
)
MINERU_CACHE_SCHEMA_VERSION = env_str("MINERU_CACHE_SCHEMA_VERSION", "v2")

# =========================
# Rerank 重排序配置
# =========================

ENABLE_RERANK = True

# Hybrid Retrieval 先召回多少个候选 chunk
RERANK_CANDIDATE_TOP_N = 12

# 每个 chunk 放进 rerank prompt 的最大字符数
RERANK_MAX_CHARS_PER_CHUNK = 1200

# Rerank 模型温度，越低越稳定
RERANK_TEMPERATURE = 0.1

# 如果 Rerank 失败，是否回退到原始 Hybrid Retrieval 结果
RERANK_FALLBACK_TO_ORIGINAL = True

# =========================
# PDF 解析质量检测配置
# =========================

ENABLE_PDF_PARSE_QUALITY_CHECK = True

PDF_QUALITY_GOOD_SCORE = 80

PDF_QUALITY_MEDIUM_SCORE = 60

PDF_QUALITY_MIN_TEXT_LENGTH = 800

PDF_QUALITY_HIGH_GARBLED_RATIO = 0.05

PDF_QUALITY_HIGH_BLANK_LINE_RATIO = 0.55

# =========================
# SQLite Memory 配置
# =========================

ENABLE_SQLITE_MEMORY = env_bool("ENABLE_SQLITE_MEMORY", True)

MEMORY_DB_PATH = env_path(
    "MEMORY_DB_PATH",
    PROJECT_ROOT / "data" / "memory.db",
)

MEMORY_HISTORY_LIMIT = 50

# =========================
# 产品主题配置：Math-learning-agent 数学学习助手
# =========================

PRODUCT_NAME = "Math-learning-agent"

PRODUCT_CHINESE_NAME = "数学学习助手"

APP_PAGE_TITLE = "Math-learning-agent 数学学习助手"

APP_TITLE = "Math-learning-agent 数学学习助手"

ENABLE_MATH_EXAM_MODE = True

# 如果你之前还有 ENABLE_STAT_EXAM_MODE，可以保留为兼容，但建议设为 False
ENABLE_STAT_EXAM_MODE = False

MATH_EXAM_SUPPORTED_SUBJECTS = [
    "小学数学",
    "初中数学",
    "高中数学",
    "大学数学",
    "高等数学",
    "线性代数",
    "概率论",
    "数理统计",
    "解析几何",
    "平面几何",
    "立体几何",
    "函数",
    "方程",
    "不等式",
    "数列",
    "三角函数",
    "导数",
    "积分",
    "微分方程",
    "矩阵",
    "向量",
]

MATH_EXAM_DEFAULT_OUTPUT_FIELDS = [
    "analysis",
    "difficulty",
    "type",
    "tags",
]

MATH_EXAM_TEMPERATURE = 0.2


# =========================
# 错题卡片与错题库配置
# =========================

ENABLE_WRONGBOOK = env_bool("ENABLE_WRONGBOOK", True)

WRONGBOOK_DB_PATH = env_path(
    "WRONGBOOK_DB_PATH",
    PROJECT_ROOT / "data" / "wrongbook.db",
)

CARD_OUTPUT_DIR = env_path(
    "CARD_OUTPUT_DIR",
    PROJECT_ROOT / "data" / "cards",
)

WRONGBOOK_PDF_OUTPUT_DIR = env_path(
    "WRONGBOOK_PDF_OUTPUT_DIR",
    PROJECT_ROOT / "data" / "wrongbook_exports",
)

CARD_IMAGE_WIDTH = 1240

CARD_MIN_IMAGE_HEIGHT = 1754

CARD_TITLE = "Math-learning-agent 数学错题卡"

CARD_FOOTER = "Math-learning-agent 数学学习助手"

CARD_FONT_PATHS = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]

# =========================
# MathJax HTML 错题卡渲染配置
# =========================

CARD_HTML_OUTPUT_DIR = env_path(
    "CARD_HTML_OUTPUT_DIR",
    PROJECT_ROOT / "data" / "card_html",
)

CARD_RENDER_USE_MATHJAX = True

CARD_SCREENSHOT_TIMEOUT_MS = 30000

CARD_HTML_VIEWPORT_WIDTH = 1240

CARD_HTML_VIEWPORT_HEIGHT = 2200

MATHJAX_CDN_URL = env_str(
    "MATHJAX_CDN_URL",
    "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js",
)
