import os
import shutil
import subprocess
import uuid
from pathlib import Path

from services.pdf_quality_service import (
    check_pdf_parse_quality,
    flatten_quality_for_metadata,
)

from langchain_core.documents import Document
from pypdf import PdfReader, PdfWriter

from config import (
    MINERU_CMD,
    MINERU_BACKEND,
    MINERU_METHOD,
    MINERU_LANG,
    MINERU_TIMEOUT_SECONDS,
    MINERU_TEMP_DIR_NAME,
    MINERU_ENABLE_PAGE_BATCH,
    MINERU_PAGE_BATCH_SIZE,
    MINERU_TRY_OCR_WHEN_AUTO_FAILS,
    MINERU_ENABLE_CACHE,
    ENABLE_PDF_PARSE_QUALITY_CHECK,
)

from services.mineru_cleaner import clean_mineru_markdown
from services.mineru_cache import (
    calculate_uploaded_file_hash,
    load_mineru_cache,
    save_mineru_cache,
)


def is_mineru_available():
    """
    检查 MinerU 命令是否可用。
    """
    mineru_path = Path(MINERU_CMD)

    if mineru_path.exists():
        return True

    if shutil.which(MINERU_CMD):
        return True

    return False


def ensure_runtime_dirs():
    """
    确保 MinerU 运行目录存在。
    """
    base_dir = Path(MINERU_TEMP_DIR_NAME)
    base_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = base_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    return base_dir, temp_dir


def save_uploaded_pdf_to_temp(uploaded_file, temp_input_dir):
    """
    将 Streamlit 上传的 PDF 保存成真实文件。
    """
    temp_input_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(uploaded_file.name).name
    pdf_path = temp_input_dir / safe_name

    uploaded_file.seek(0)
    pdf_path.write_bytes(uploaded_file.read())
    uploaded_file.seek(0)

    return pdf_path


def get_pdf_page_count(pdf_path):
    """
    获取 PDF 页数。
    """
    try:
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)
    except Exception:
        return 0


def split_pdf_by_pages(pdf_path, output_dir, batch_size):
    """
    将 PDF 按页拆分成多个小 PDF。
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)

    batch_pdf_paths = []

    for start_page in range(0, total_pages, batch_size):
        end_page = min(start_page + batch_size, total_pages)

        writer = PdfWriter()

        for page_index in range(start_page, end_page):
            writer.add_page(reader.pages[page_index])

        batch_pdf_path = output_dir / f"batch_{start_page + 1}_{end_page}.pdf"

        with batch_pdf_path.open("wb") as f:
            writer.write(f)

        batch_pdf_paths.append(
            {
                "path": batch_pdf_path,
                "start_page": start_page + 1,
                "end_page": end_page,
            }
        )

    return batch_pdf_paths


def run_mineru_on_pdf(pdf_path, output_dir, method=None):
    """
    调用 MinerU CLI 解析 PDF。
    """
    _, temp_dir = ensure_runtime_dirs()

    output_dir.mkdir(parents=True, exist_ok=True)

    if method is None:
        method = MINERU_METHOD

    cmd = [
        str(MINERU_CMD),
        "-p",
        str(pdf_path),
        "-o",
        str(output_dir),
        "-b",
        MINERU_BACKEND,
        "-m",
        method,
        "-l",
        MINERU_LANG,
    ]

    env = os.environ.copy()
    env["TMP"] = str(temp_dir)
    env["TEMP"] = str(temp_dir)

    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="ignore",
        timeout=MINERU_TIMEOUT_SECONDS,
        env=env,
    )

    return result, cmd


def find_best_markdown_file(output_dir):
    """
    MinerU 输出目录中可能有多个 Markdown 文件。
    这里选择文件大小最大的 md。
    """
    md_files = list(output_dir.rglob("*.md"))

    if not md_files:
        return None

    md_files = sorted(
        md_files,
        key=lambda p: p.stat().st_size if p.exists() else 0,
        reverse=True,
    )

    return md_files[0]


def read_markdown_from_mineru_output(output_dir):
    """
    从 MinerU 输出目录读取 Markdown。
    """
    md_file = find_best_markdown_file(output_dir)

    if md_file is None:
        return "", None

    markdown_text = md_file.read_text(
        encoding="utf-8",
        errors="ignore",
    ).strip()

    return markdown_text, md_file


def run_mineru_and_read_markdown(pdf_path, output_dir, method=None):
    """
    运行 MinerU 并读取 Markdown。
    """
    result, cmd = run_mineru_on_pdf(
        pdf_path=pdf_path,
        output_dir=output_dir,
        method=method,
    )

    if result.returncode != 0:
        return {
            "success": False,
            "markdown_text": "",
            "md_file": None,
            "cmd": cmd,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": f"MinerU 解析失败，returncode={result.returncode}",
        }

    markdown_text, md_file = read_markdown_from_mineru_output(output_dir)

    if not markdown_text:
        return {
            "success": False,
            "markdown_text": "",
            "md_file": md_file,
            "cmd": cmd,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": "MinerU 没有生成有效 Markdown。",
        }

    return {
        "success": True,
        "markdown_text": markdown_text,
        "md_file": md_file,
        "cmd": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": "",
    }


def read_pdf_with_mineru_single(pdf_path, output_dir):
    """
    单个 PDF 直接使用 MinerU 解析。
    """
    result = run_mineru_and_read_markdown(
        pdf_path=pdf_path,
        output_dir=output_dir,
        method=MINERU_METHOD,
    )

    if result["success"]:
        return result

    if MINERU_TRY_OCR_WHEN_AUTO_FAILS and MINERU_METHOD != "ocr":
        ocr_output_dir = output_dir.parent / f"{output_dir.name}_ocr"

        ocr_result = run_mineru_and_read_markdown(
            pdf_path=pdf_path,
            output_dir=ocr_output_dir,
            method="ocr",
        )

        if ocr_result["success"]:
            ocr_result["error"] = "auto 模式失败后，ocr 模式解析成功。"
            return ocr_result

    return result


def read_pdf_with_mineru_batches(pdf_path, batch_dir, output_base_dir, batch_size):
    """
    大 PDF 按页拆分后，逐批调用 MinerU，再合并 Markdown。
    """
    errors = []
    markdown_parts = []
    md_paths = []

    batch_pdf_infos = split_pdf_by_pages(
        pdf_path=pdf_path,
        output_dir=batch_dir,
        batch_size=batch_size,
    )

    for batch_index, batch_info in enumerate(batch_pdf_infos, start=1):
        batch_pdf_path = batch_info["path"]
        start_page = batch_info["start_page"]
        end_page = batch_info["end_page"]

        batch_output_dir = output_base_dir / f"batch_{batch_index}_{start_page}_{end_page}"

        try:
            result = read_pdf_with_mineru_single(
                pdf_path=batch_pdf_path,
                output_dir=batch_output_dir,
            )

            if result["success"]:
                markdown_parts.append(
                    f"\n\n<!-- pages {start_page}-{end_page} -->\n\n"
                    f"{result['markdown_text']}"
                )

                if result["md_file"]:
                    md_paths.append(str(result["md_file"]))

            else:
                errors.append(
                    f"第 {start_page}-{end_page} 页 MinerU 解析失败：{result['error']}\n"
                    f"命令：{' '.join(map(str, result.get('cmd', [])))}\n"
                    f"STDERR：{result.get('stderr', '')[:1000]}"
                )

        except subprocess.TimeoutExpired:
            errors.append(
                f"第 {start_page}-{end_page} 页 MinerU 解析超时，超过 {MINERU_TIMEOUT_SECONDS} 秒。"
            )

        except Exception as e:
            errors.append(
                f"第 {start_page}-{end_page} 页 MinerU 解析异常：{e}"
            )

    merged_markdown = "\n\n".join(markdown_parts).strip()

    return {
        "success": bool(merged_markdown),
        "markdown_text": merged_markdown,
        "md_paths": md_paths,
        "errors": errors,
        "batch_count": len(batch_pdf_infos),
    }

def build_quality_result(markdown_text):
    """
    构造 PDF 解析质量检测结果。
    """
    if not ENABLE_PDF_PARSE_QUALITY_CHECK:
        return {}

    return check_pdf_parse_quality(markdown_text)


def build_quality_metadata(quality_result):
    """
    构造适合 Document metadata 的质量检测字段。
    """
    if not quality_result:
        return {}

    return flatten_quality_for_metadata(quality_result)

def build_cache_document(uploaded_file, file_hash, cache_result):
    """
    根据缓存 Markdown 构造 Document。
    """
    cache_metadata = cache_result.get("metadata", {})
    markdown_text = cache_result.get("markdown_text", "")

    quality_result = cache_metadata.get("pdf_parse_quality", {})

    # 兼容老缓存：
    # 如果以前的缓存没有质量检测信息，就现场检测一次。
    if not quality_result and ENABLE_PDF_PARSE_QUALITY_CHECK:
        quality_result = build_quality_result(markdown_text)

    quality_metadata = build_quality_metadata(quality_result)

    documents = [
        Document(
            page_content=markdown_text,
            metadata={
                "source": uploaded_file.name,
                "file_type": "pdf_mineru_cache",
                "location": "MinerU Markdown 缓存",
                "mineru_from_cache": True,
                "mineru_cache_path": cache_result.get("markdown_path", ""),
                "mineru_file_hash": file_hash,
                "mineru_method": cache_metadata.get("mineru_method", MINERU_METHOD),
                "mineru_lang": cache_metadata.get("mineru_lang", MINERU_LANG),
                "mineru_page_count": cache_metadata.get("page_count", ""),
                "mineru_parse_mode": cache_metadata.get("parse_mode", ""),
                **quality_metadata,
            },
        )
    ]

    return documents


def read_pdf_with_mineru(uploaded_file):
    """
    使用 MinerU 将 PDF 解析成 Markdown，再转成 LangChain Document。

    加入缓存逻辑：
    - 如果缓存存在，直接读取缓存
    - 如果缓存不存在，再调用 MinerU
    - 解析成功后写入缓存
    """
    documents = []
    errors = []

    if not is_mineru_available():
        errors.append(
            f"MinerU 不可用，请检查 MINERU_CMD 路径：{MINERU_CMD}"
        )
        return documents, errors

    try:
        file_hash = calculate_uploaded_file_hash(uploaded_file)

        if MINERU_ENABLE_CACHE:
            cache_result = load_mineru_cache(file_hash)

            if cache_result["hit"]:
                documents = build_cache_document(
                    uploaded_file=uploaded_file,
                    file_hash=file_hash,
                    cache_result=cache_result,
                )

                return documents, errors

        run_id = uuid.uuid4().hex[:8]

        base_temp_dir = Path(MINERU_TEMP_DIR_NAME)
        input_dir = base_temp_dir / run_id / "input"
        output_dir = base_temp_dir / run_id / "output"
        batch_dir = base_temp_dir / run_id / "batches"

        pdf_path = save_uploaded_pdf_to_temp(
            uploaded_file=uploaded_file,
            temp_input_dir=input_dir,
        )

        page_count = get_pdf_page_count(pdf_path)

        if (
            MINERU_ENABLE_PAGE_BATCH
            and page_count > MINERU_PAGE_BATCH_SIZE
        ):
            batch_result = read_pdf_with_mineru_batches(
                pdf_path=pdf_path,
                batch_dir=batch_dir,
                output_base_dir=output_dir,
                batch_size=MINERU_PAGE_BATCH_SIZE,
            )

            if not batch_result["success"]:
                errors.append(
                    "MinerU 分批解析失败，已准备回退到 pypdf。\n"
                    + "\n".join(batch_result["errors"])
                )
                return documents, errors

            if batch_result["errors"]:
                errors.append(
                    "MinerU 分批解析存在失败，已准备回退到 pypdf，避免只索引部分页码。\n"
                    + "\n".join(batch_result["errors"])
                )
                return documents, errors

            cleaned_markdown = clean_mineru_markdown(
                batch_result["markdown_text"]
            )

            quality_result = build_quality_result(cleaned_markdown)
            quality_metadata = build_quality_metadata(quality_result)

            if MINERU_ENABLE_CACHE:
                cache_save_result = save_mineru_cache(
                    file_hash=file_hash,
                    markdown_text=cleaned_markdown,
                    original_file_name=uploaded_file.name,
                    page_count=page_count,
                    parse_mode="batch",
                    extra_metadata={
                        "mineru_batch_count": batch_result["batch_count"],
                        "mineru_md_paths": batch_result["md_paths"],
                        "pdf_parse_quality": quality_result,
                    },
                )
            else:
                cache_save_result = {
                    "metadata": {},
                    "markdown_path": "",
                }

            documents.append(
                Document(
                    page_content=cleaned_markdown,
                    metadata={
                        "source": uploaded_file.name,
                        "file_type": "pdf_mineru",
                        "location": f"MinerU Markdown 分批解析，共 {page_count} 页",
                        "mineru_from_cache": False,
                        "mineru_file_hash": file_hash,
                        "mineru_cache_path": cache_save_result.get("markdown_path", ""),
                        "mineru_page_count": page_count,
                        "mineru_batch_count": batch_result["batch_count"],
                        "mineru_md_paths": str(batch_result["md_paths"]),
                        "mineru_method": MINERU_METHOD,
                        "mineru_lang": MINERU_LANG,
                        "mineru_parse_mode": "batch",
                        **quality_metadata,
                    },
                )
            )

            return documents, errors

        single_result = read_pdf_with_mineru_single(
            pdf_path=pdf_path,
            output_dir=output_dir,
        )

        if not single_result["success"]:
            errors.append(
                "MinerU 解析失败，已准备回退到 pypdf。\n"
                f"错误：{single_result['error']}\n"
                f"命令：{' '.join(map(str, single_result.get('cmd', [])))}\n"
                f"STDERR：{single_result.get('stderr', '')[:1000]}"
            )
            return documents, errors

        cleaned_markdown = clean_mineru_markdown(
            single_result["markdown_text"]
        )
        quality_result = build_quality_result(cleaned_markdown)
        quality_metadata = build_quality_metadata(quality_result)

        if MINERU_ENABLE_CACHE:
            cache_save_result = save_mineru_cache(
                file_hash=file_hash,
                markdown_text=cleaned_markdown,
                original_file_name=uploaded_file.name,
                page_count=page_count,
                parse_mode="single",
                extra_metadata={
                    "mineru_md_path": str(single_result["md_file"]),
                    "pdf_parse_quality": quality_result,
                },
            )
        else:
            cache_save_result = {
                "metadata": {},
                "markdown_path": "",
            }

        documents.append(
            Document(
                page_content=cleaned_markdown,
                metadata={
                    "source": uploaded_file.name,
                    "file_type": "pdf_mineru",
                    "location": f"MinerU Markdown，共 {page_count} 页",
                    "mineru_from_cache": False,
                    "mineru_file_hash": file_hash,
                    "mineru_cache_path": cache_save_result.get("markdown_path", ""),
                    "mineru_page_count": page_count,
                    "mineru_md_path": str(single_result["md_file"]),
                    "mineru_method": MINERU_METHOD,
                    "mineru_lang": MINERU_LANG,
                    "mineru_parse_mode": "single",
                    **quality_metadata,
                },
            )
        )

        return documents, errors

    except subprocess.TimeoutExpired:
        errors.append(
            f"MinerU 解析超时，超过 {MINERU_TIMEOUT_SECONDS} 秒，已准备回退到 pypdf。"
        )
        return documents, errors

    except Exception as e:
        errors.append(
            f"MinerU 解析异常：{e}，已准备回退到 pypdf。"
        )
        return documents, errors
