import argparse
import importlib.util
import os
import shutil
import sqlite3
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def ok(message):
    print(f"[OK] {message}")


def warn(message):
    print(f"[WARN] {message}")


def fail(message):
    print(f"[FAIL] {message}")


def is_placeholder(value):
    if not value:
        return False
    lowered = value.strip().lower()
    return lowered in {
        "replace-with-your-api-key",
        "your-api-key",
        "sk-xxx",
        "changeme",
    }


def env_path(name, default):
    value = Path(os.getenv(name, default)).expanduser()
    if value.is_absolute():
        return value
    return PROJECT_ROOT / value


def check_required_env():
    failures = 0

    api_key = os.getenv("QWEN_API_KEY", "")
    base_url = os.getenv("QWEN_BASE_URL", "")

    if not api_key:
        fail("QWEN_API_KEY is missing in .env")
        failures += 1
    elif is_placeholder(api_key):
        fail("QWEN_API_KEY is still a placeholder")
        failures += 1
    else:
        ok("QWEN_API_KEY is configured (value hidden)")

    if not base_url:
        fail("QWEN_BASE_URL is missing in .env")
        failures += 1
    elif not urlparse(base_url).scheme:
        fail("QWEN_BASE_URL must be an absolute URL")
        failures += 1
    else:
        ok(f"QWEN_BASE_URL is configured: {base_url}")

    for name in ("QWEN_CHAT_MODEL", "QWEN_OCR_MODEL", "QWEN_EMBEDDING_MODEL"):
        value = os.getenv(name, "")
        if value:
            ok(f"{name}={value}")
        else:
            warn(f"{name} is not set; code default will be used")

    return failures


def check_imports():
    failures = 0
    modules = [
        "streamlit",
        "dotenv",
        "langchain_openai",
        "langchain_community",
        "langgraph",
        "chromadb",
        "pypdf",
        "docx",
        "PIL",
        "reportlab",
    ]

    for module in modules:
        if importlib.util.find_spec(module):
            ok(f"Python package importable: {module}")
        else:
            fail(f"Python package missing: {module}")
            failures += 1

    return failures


def check_mineru():
    mineru_cmd = os.getenv("MINERU_CMD", ".venv/Scripts/mineru.exe")
    mineru_path = env_path("MINERU_CMD", mineru_cmd)
    command = str(mineru_path) if mineru_path.exists() else mineru_cmd

    if mineru_path.exists() or shutil.which(mineru_cmd):
        ok(f"MinerU command found: {command}")
        return 0

    warn(
        "MinerU command not found. PDF parsing can fall back to pypdf, "
        "or install dependencies from requirements.txt and set MINERU_CMD."
    )
    return 0


def check_playwright():
    if not importlib.util.find_spec("playwright"):
        warn("Playwright package missing. HTML card rendering will fail until installed.")
        return 0

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        ok("Playwright Chromium launches")
    except Exception as exc:
        warn(
            "Playwright is installed but Chromium is not ready. "
            "Run: .\\.venv\\Scripts\\playwright.exe install chromium. "
            f"Details: {exc}"
        )
    return 0


def check_sqlite_paths():
    failures = 0
    paths = [
        env_path("MEMORY_DB_PATH", "data/memory.db"),
        env_path("WRONGBOOK_DB_PATH", "data/wrongbook.db"),
    ]

    for db_path in paths:
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(db_path) as conn:
                conn.execute("select 1")
            ok(f"SQLite path writable: {db_path}")
        except Exception as exc:
            fail(f"SQLite path is not writable: {db_path} ({exc})")
            failures += 1

    return failures


def check_runtime_dirs():
    failures = 0
    for name, default in [
        ("MINERU_TEMP_DIR_NAME", "mineru_runtime"),
        ("MINERU_CACHE_DIR_NAME", "cache/mineru_markdown"),
        ("CARD_OUTPUT_DIR", "data/cards"),
        ("CARD_HTML_OUTPUT_DIR", "data/card_html"),
        ("WRONGBOOK_PDF_OUTPUT_DIR", "data/wrongbook_exports"),
    ]:
        path = env_path(name, default)
        try:
            path.mkdir(parents=True, exist_ok=True)
            ok(f"{name} writable: {path}")
        except Exception as exc:
            fail(f"{name} is not writable: {path} ({exc})")
            failures += 1
    return failures


def check_mathjax(online):
    url = os.getenv(
        "MATHJAX_CDN_URL",
        "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js",
    )

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        fail("MATHJAX_CDN_URL must be an http(s) URL")
        return 1

    ok(f"MATHJAX_CDN_URL configured: {url}")

    if not online:
        warn("Skipping MathJax CDN network check; pass --online to test access.")
        return 0

    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status < 400:
                ok("MathJax CDN reachable")
                return 0
            fail(f"MathJax CDN returned HTTP {response.status}")
            return 1
    except Exception as exc:
        fail(f"MathJax CDN check failed: {exc}")
        return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--online",
        action="store_true",
        help="also check network access to MathJax CDN",
    )
    args = parser.parse_args()

    failures = 0
    failures += check_required_env()
    failures += check_imports()
    failures += check_mineru()
    failures += check_playwright()
    failures += check_sqlite_paths()
    failures += check_runtime_dirs()
    failures += check_mathjax(args.online)

    if failures:
        print(f"\nEnvironment check failed with {failures} blocking issue(s).")
        return 1

    print("\nEnvironment check completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
