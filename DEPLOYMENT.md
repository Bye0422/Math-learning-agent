# Local Setup and Deployment Checks

This file is kept in plain ASCII so it stays readable across Windows terminals
and editors.

## 1. Create local environment

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For HTML card screenshots:

```powershell
.\.venv\Scripts\playwright.exe install chromium
```

`requirements.txt` is the single curated dependency list for the Streamlit app,
Qwen API, LangGraph, Chroma, document parsing, PDF export, MinerU, and the
Playwright Python package. The Chromium browser binary is installed separately
with the Playwright command above.

## 2. Configure secrets

Copy `.env.example` to `.env` and fill only local values:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env` or any file containing a real API key. If a real key was
ever shared, committed, or pasted into a ticket, rotate it immediately and
inspect Git history before publishing the repository.

## 3. Run preflight checks

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
```

The check covers:

- Qwen config presence without printing the API key.
- Core Python packages.
- MinerU command availability.
- Playwright Chromium launch.
- SQLite database paths.
- Runtime output/cache directories.
- MathJax CDN URL shape.

To also test MathJax CDN network access:

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py --online
```

## 4. Start the app

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

## 5. Docker deployment

The Docker image is built from `requirements.txt`. Playwright browser binaries
may still need to be installed in a deployment-specific image layer.

Build the image:

```powershell
docker build -t math-learning-agent:core .
```

Run the Streamlit app:

```powershell
docker run --rm -p 8501:8501 --env-file .env `
  -v ${PWD}/data:/app/data `
  -v ${PWD}/cache:/app/cache `
  -v ${PWD}/logs:/app/logs `
  -v ${PWD}/mineru_runtime:/app/mineru_runtime `
  math-learning-agent:core
```

Open `http://localhost:8501`.

The `.dockerignore` file excludes `.env`, `data/`, `cache/`, `logs/`, and
`mineru_runtime/` so local secrets and runtime artifacts are not baked into the
image.

For Linux or macOS shells, use `$(pwd)` instead of `${PWD}` if needed and remove
PowerShell line-continuation backticks.

### Optional MinerU in containers

MinerU is included in `requirements.txt`, but the app still falls back to
`pypdf` when MinerU is not available. If a deployment requires MinerU-enhanced
PDF parsing, make sure the image has any MinerU system/runtime requirements and
sets `MINERU_CMD` to the command path inside the container.

Do not mount or copy a local `.venv` into the container.

## 6. Runtime cleanup

Runtime folders can grow during PDF parsing and vector-store rebuilds. Preview a
cleanup first:

```powershell
.\.venv\Scripts\python.exe scripts\clean_runtime.py
```

Apply cleanup:

```powershell
.\.venv\Scripts\python.exe scripts\clean_runtime.py --apply
```

The script targets runtime output only: `mineru_runtime`, `logs`, and
`cache/vector_store`. It does not remove `.env`, source files, tests, or saved
wrongbook data.

## 7. Run tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 8. Validation harness

For a local pre-deployment pass:

```powershell
.\.venv\Scripts\python.exe scripts\run_harness.py --mode quick
```

For a Streamlit smoke test as well:

```powershell
.\.venv\Scripts\python.exe scripts\run_harness.py --mode full --port 8501
```

`--online` enables the MathJax CDN check in `scripts/check_env.py`. `--eval`
adds Eval V2 in full mode and may call LLM APIs.

## 9. Environment variables

Required:

- `QWEN_API_KEY`: Qwen/DashScope API key. Keep this in `.env` or the deployment
  secret manager.
- `QWEN_BASE_URL`: OpenAI-compatible API base URL, for example
  `https://dashscope.aliyuncs.com/compatible-mode/v1`.

Common model settings:

- `QWEN_CHAT_MODEL`: chat model name.
- `QWEN_OCR_MODEL`: vision/OCR-capable model name.
- `QWEN_EMBEDDING_MODEL`: embedding model name.

Runtime feature flags and paths:

- `USE_MINERU_FOR_PDF`: enable MinerU attempt before `pypdf` fallback.
- `MINERU_CMD`: MinerU executable path when MinerU is installed.
- `MINERU_TEMP_DIR_NAME`: temporary MinerU runtime directory.
- `MINERU_CACHE_DIR_NAME`: MinerU Markdown cache directory.
- `ENABLE_VECTOR_CACHE`: enable persisted vector cache.
- `VECTOR_CACHE_DIR_NAME`: vector cache directory.
- `ENABLE_SQLITE_MEMORY`: enable SQLite conversation memory.
- `MEMORY_DB_PATH`: memory SQLite database path.
- `ENABLE_WRONGBOOK`: enable wrongbook/card features.
- `WRONGBOOK_DB_PATH`: wrongbook SQLite database path.
- `CARD_OUTPUT_DIR`: generated card image directory.
- `CARD_HTML_OUTPUT_DIR`: generated card HTML directory.
- `WRONGBOOK_PDF_OUTPUT_DIR`: exported wrongbook PDF directory.
- `MATHJAX_CDN_URL`: MathJax script URL for HTML card rendering.

Use `.env.example` as the source of default values. Never bake real API keys
into an image.

## 10. Data volume recommendations

Persist these directories outside the container or on a durable server volume:

- `data/`: SQLite databases, cards, exports, and user-facing generated files.
- `cache/`: vector stores and MinerU Markdown cache.
- `logs/`: CSV agent run logs.
- `mineru_runtime/`: MinerU temporary working files when MinerU is enabled.

For production-like deployments, back up `data/` first. Cache directories can
usually be rebuilt, but keeping them improves cold-start and repeated PDF
processing time.

## Deployment notes

- Keep runtime paths relative to the project unless deployment needs an
  absolute external volume. The defaults write to `data/`, `cache/`, and
  `mineru_runtime/`.
- MinerU is optional. If it is unavailable, PDF parsing should fall back to
  `pypdf` with a readable warning.
- Playwright requires browser installation after the Python package install.
  Run `playwright install chromium` when HTML card rendering fails.
- MathJax is loaded from CDN by default. Offline deployments should either
  allow this URL or set `MATHJAX_CDN_URL` to an internally hosted copy.
