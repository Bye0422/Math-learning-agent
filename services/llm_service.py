import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import (
    ANSWER_TEMPERATURE,
    OCR_TEMPERATURE,
    EMBEDDING_BATCH_SIZE,
    CHECK_EMBEDDING_CTX_LENGTH,
    TIKTOKEN_ENABLED,
)


load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL")
QWEN_CHAT_MODEL = os.getenv("QWEN_CHAT_MODEL", "qwen3.7-plus")
QWEN_OCR_MODEL = os.getenv("QWEN_OCR_MODEL", QWEN_CHAT_MODEL)
QWEN_EMBEDDING_MODEL = os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v4")


def check_env():
    """
    检查必要环境变量。
    """
    if not QWEN_API_KEY:
        raise RuntimeError("没有读取到 QWEN_API_KEY，请检查 .env 文件。")

    if not QWEN_BASE_URL:
        raise RuntimeError("没有读取到 QWEN_BASE_URL，请检查 .env 文件。")


def get_chat_llm(temperature=ANSWER_TEMPERATURE, model=None):
    """
    创建聊天模型。
    用于任务识别、问题改写、答案生成、格式修复等。
    """
    check_env()

    return ChatOpenAI(
        model=model or QWEN_CHAT_MODEL,
        api_key=QWEN_API_KEY,
        base_url=QWEN_BASE_URL,
        temperature=temperature,
    )


def get_ocr_llm():
    """
    创建 OCR / 多模态模型。
    """
    check_env()

    return ChatOpenAI(
        model=QWEN_OCR_MODEL,
        api_key=QWEN_API_KEY,
        base_url=QWEN_BASE_URL,
        temperature=OCR_TEMPERATURE,
    )


def get_embeddings():
    """
    创建 embedding 模型。
    注意：qwen3.7-plus 是聊天模型，text-embedding-v4 才是向量模型。
    """
    check_env()

    return OpenAIEmbeddings(
        model=QWEN_EMBEDDING_MODEL,
        api_key=QWEN_API_KEY,
        base_url=QWEN_BASE_URL,
        tiktoken_enabled=TIKTOKEN_ENABLED,
        check_embedding_ctx_length=CHECK_EMBEDDING_CTX_LENGTH,
        chunk_size=EMBEDDING_BATCH_SIZE,
    )