import hashlib
import json
from datetime import datetime
from pathlib import Path

from config import (
    MINERU_CACHE_DIR_NAME,
    MINERU_CACHE_SCHEMA_VERSION,
    MINERU_METHOD,
    MINERU_LANG,
    MINERU_PAGE_BATCH_SIZE,
)


def ensure_mineru_cache_dir():
    """
    确保 MinerU 缓存目录存在。
    """
    cache_dir = Path(MINERU_CACHE_DIR_NAME)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def calculate_uploaded_file_hash(uploaded_file):
    """
    计算上传 PDF 的 sha256 hash。

    注意：
    Streamlit 的 uploaded_file 读完后指针会移动，所以这里读完要 seek(0)。
    """
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    return hashlib.sha256(file_bytes).hexdigest()


def build_cache_key(file_hash):
    """
    构造缓存 key。

    加入 method、lang、batch_size 是为了避免配置变化后读到旧缓存。
    """
    return (
        f"{file_hash}"
        f"__schema_{MINERU_CACHE_SCHEMA_VERSION}"
        f"__method_{MINERU_METHOD}"
        f"__lang_{MINERU_LANG}"
        f"__batch_{MINERU_PAGE_BATCH_SIZE}"
    )


def get_cache_paths(file_hash):
    """
    根据文件 hash 获取缓存 Markdown 和 metadata 路径。
    """
    cache_dir = ensure_mineru_cache_dir()
    cache_key = build_cache_key(file_hash)

    markdown_path = cache_dir / f"{cache_key}.md"
    metadata_path = cache_dir / f"{cache_key}.json"

    return markdown_path, metadata_path


def load_mineru_cache(file_hash):
    """
    读取 MinerU 缓存。

    返回：
    {
        "hit": bool,
        "markdown_text": str,
        "metadata": dict,
        "markdown_path": str,
        "metadata_path": str,
    }
    """
    markdown_path, metadata_path = get_cache_paths(file_hash)

    if not markdown_path.exists():
        return {
            "hit": False,
            "markdown_text": "",
            "metadata": {},
            "markdown_path": str(markdown_path),
            "metadata_path": str(metadata_path),
        }

    markdown_text = markdown_path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).strip()

    if not markdown_text:
        return {
            "hit": False,
            "markdown_text": "",
            "metadata": {},
            "markdown_path": str(markdown_path),
            "metadata_path": str(metadata_path),
        }

    metadata = {}

    if metadata_path.exists():
        try:
            metadata = json.loads(
                metadata_path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )
        except Exception:
            metadata = {}

    return {
        "hit": True,
        "markdown_text": markdown_text,
        "metadata": metadata,
        "markdown_path": str(markdown_path),
        "metadata_path": str(metadata_path),
    }


def save_mineru_cache(
    file_hash,
    markdown_text,
    original_file_name,
    page_count,
    parse_mode,
    extra_metadata=None,
):
    """
    保存 MinerU Markdown 缓存。
    """
    markdown_path, metadata_path = get_cache_paths(file_hash)

    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(
        markdown_text,
        encoding="utf-8",
    )

    metadata = {
        "original_file_name": original_file_name,
        "file_hash": file_hash,
        "page_count": page_count,
        "parse_mode": parse_mode,
        "mineru_cache_schema_version": MINERU_CACHE_SCHEMA_VERSION,
        "mineru_method": MINERU_METHOD,
        "mineru_lang": MINERU_LANG,
        "mineru_page_batch_size": MINERU_PAGE_BATCH_SIZE,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "markdown_path": str(markdown_path),
    }

    if extra_metadata:
        metadata.update(extra_metadata)

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "markdown_path": str(markdown_path),
        "metadata_path": str(metadata_path),
        "metadata": metadata,
    }


def clear_mineru_cache():
    """
    清空 MinerU Markdown 缓存。
    """
    cache_dir = ensure_mineru_cache_dir()

    removed_count = 0

    for path in cache_dir.glob("*"):
        if path.is_file():
            path.unlink()
            removed_count += 1

    return removed_count
