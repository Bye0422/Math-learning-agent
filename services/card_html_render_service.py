import hashlib
import html
import re
import uuid
from datetime import datetime
from pathlib import Path

from config import (
    CARD_OUTPUT_DIR,
    CARD_TITLE,
    CARD_HTML_OUTPUT_DIR,
    CARD_HTML_VIEWPORT_WIDTH,
    CARD_HTML_VIEWPORT_HEIGHT,
    CARD_SCREENSHOT_TIMEOUT_MS,
    MATHJAX_CDN_URL,
)

try:
    from config import CARD_FOOTER
except Exception:
    CARD_FOOTER = "MathCard Agent"


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_output_dirs():
    card_dir = ensure_dir(CARD_OUTPUT_DIR)
    html_dir = ensure_dir(CARD_HTML_OUTPUT_DIR)
    return card_dir, html_dir


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_difficulty(value):
    try:
        value = int(value)
    except Exception:
        value = 2

    if value < 1:
        value = 1

    if value > 5:
        value = 5

    return value


def difficulty_to_stars(value):
    value = normalize_difficulty(value)
    return "★" * value + "☆" * (5 - value)


def normalize_tags(tags):
    if isinstance(tags, list):
        cleaned = [str(tag).strip() for tag in tags if str(tag).strip()]
    elif isinstance(tags, str):
        cleaned = [
            tag.strip()
            for tag in re.split(r"[，,、;/；\s]+", tags)
            if tag.strip()
        ]
    else:
        cleaned = ["数学"]

    if not cleaned:
        cleaned = ["数学"]

    return cleaned[:4]


def build_card_id(question_text, item):
    raw = (
        f"{question_text}|"
        f"{item.get('analysis', '')}|"
        f"{item.get('difficulty', '')}|"
        f"{item.get('type', '')}|"
        f"{now_text()}|"
        f"{uuid.uuid4().hex[:8]}"
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def escape_keep_latex(text):
    """
    HTML 转义，但保留 LaTeX 里的 $、\\ 等符号。

    html.escape 不会破坏反斜杠和美元符号，
    所以 MathJax 仍然可以识别 $...$、$$...$$、\\(...\\)、\\[...\\]。
    """
    text = safe_text(text)
    return html.escape(text, quote=False)


def normalize_display_text(text):
    """
    简单清洗展示文本。
    """
    text = safe_text(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_tag_html(tags):
    parts = []

    for tag in tags:
        tag = html.escape(str(tag), quote=False)
        parts.append(f'<span class="tag">{tag}</span>')

    return "\n".join(parts)


def build_math_card_html(question_text, item):
    """
    根据结构化错题数据生成 HTML。
    LaTeX 仍然以 $...$ 形式保留，交给 MathJax 渲染。
    """
    question_text = normalize_display_text(question_text)
    analysis = normalize_display_text(item.get("analysis", ""))

    difficulty = normalize_difficulty(item.get("difficulty", 2))
    question_type = safe_text(item.get("type", "计算题"))
    tags = normalize_tags(item.get("tags", []))

    stars = difficulty_to_stars(difficulty)

    question_html = escape_keep_latex(question_text)
    analysis_html = escape_keep_latex(analysis)
    question_type_html = html.escape(question_type, quote=False)
    tags_html = build_tag_html(tags)

    created_at = now_text()

    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />

<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true
  }},
  chtml: {{
    scale: 1.0
  }},
  startup: {{
    pageReady: () => {{
      return MathJax.startup.defaultPageReady().then(() => {{
        window.__mathJaxReady = true;
      }});
    }}
  }}
}};
</script>
<script src="{MATHJAX_CDN_URL}"></script>

<style>
* {{
  box-sizing: border-box;
}}

html, body {{
  margin: 0;
  padding: 0;
  background: #eef2f7;
  font-family: "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
  color: #172033;
}}

.page {{
  width: 1240px;
  padding: 42px;
  background: #eef2f7;
}}

.card {{
  width: 1156px;
  background: #ffffff;
  border: 2px solid #dce3ee;
  border-radius: 32px;
  padding: 54px 64px 58px 64px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
}}

.header {{
  display: flex;
  justify-content: space-between;
  gap: 32px;
  align-items: flex-start;
  margin-bottom: 28px;
}}

.title {{
  font-size: 46px;
  font-weight: 800;
  color: #14213d;
  line-height: 1.2;
}}

.time {{
  margin-top: 12px;
  font-size: 24px;
  color: #718096;
}}

.brand {{
  font-size: 24px;
  color: #64748b;
  padding-top: 12px;
  white-space: nowrap;
}}

.meta {{
  margin: 22px 0 38px 0;
  padding: 20px 24px;
  border-radius: 18px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  font-size: 28px;
  line-height: 1.5;
}}

.stars {{
  letter-spacing: 2px;
}}

.tags {{
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}}

.tag {{
  display: inline-block;
  padding: 8px 16px;
  border-radius: 999px;
  background: #e0f2fe;
  border: 1px solid #bae6fd;
  color: #075985;
  font-size: 24px;
}}

.section {{
  margin-top: 36px;
}}

.section-title {{
  font-size: 32px;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 18px;
  padding-left: 16px;
  border-left: 8px solid #2563eb;
}}

.content {{
  font-size: 30px;
  line-height: 1.85;
  color: #2d3748;
  white-space: pre-wrap;
  word-break: break-word;
}}

.divider {{
  margin: 42px 0 32px 0;
  height: 2px;
  background: #e2e8f0;
}}

.footer {{
  margin-top: 46px;
  font-size: 24px;
  color: #94a3b8;
}}

mjx-container {{
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
}}

mjx-container[jax="CHTML"][display="true"] {{
  margin: 18px 0 !important;
}}
</style>
</head>

<body>
  <div class="page">
    <div class="card" id="card-root">
      <div class="header">
        <div>
          <div class="title">{html.escape(CARD_TITLE, quote=False)}</div>
          <div class="time">生成时间：{created_at}</div>
        </div>
        <div class="brand">{html.escape(CARD_FOOTER, quote=False)}</div>
      </div>

      <div class="meta">
        <div>难度：<span class="stars">{stars}</span></div>
        <div>题型：{question_type_html}</div>
        <div class="tags">{tags_html}</div>
      </div>

      <div class="section">
        <div class="section-title">题干</div>
        <div class="content">{question_html}</div>
      </div>

      <div class="divider"></div>

      <div class="section">
        <div class="section-title">解析</div>
        <div class="content">{analysis_html}</div>
      </div>

      <div class="footer">{html.escape(CARD_FOOTER, quote=False)}</div>
    </div>
  </div>
</body>
</html>
""".strip()


def write_html_file(html_text, html_path):
    html_path = Path(html_path)
    html_path.write_text(html_text, encoding="utf-8")
    return str(html_path)


def screenshot_html_to_png(page, html_path, png_path):
    """
    使用 Playwright 打开本地 HTML，等待 MathJax 渲染完成后截图。
    """
    html_path = Path(html_path).resolve()
    png_path = Path(png_path).resolve()

    page.goto(html_path.as_uri(), wait_until="networkidle")

    try:
        page.wait_for_function(
            "window.__mathJaxReady === true",
            timeout=CARD_SCREENSHOT_TIMEOUT_MS,
        )
    except Exception:
        # 即使 MathJax 等待失败，也截图，避免整个流程中断
        pass

    page.wait_for_timeout(500)

    card = page.locator("#card-root")
    card.screenshot(path=str(png_path))

    return str(png_path)


def render_html_card_to_image_with_page(
    page,
    question_text,
    item,
):
    """
    单张错题卡：结构化数据 → HTML → MathJax 渲染 → PNG。
    """
    card_dir, html_dir = ensure_output_dirs()

    card_id = build_card_id(question_text, item)

    html_path = html_dir / f"math_card_{card_id}.html"
    png_path = card_dir / f"math_card_{card_id}.png"

    html_text = build_math_card_html(
        question_text=question_text,
        item=item,
    )

    write_html_file(html_text, html_path)

    screenshot_html_to_png(
        page=page,
        html_path=html_path,
        png_path=png_path,
    )

    return {
        "html_path": str(html_path),
        "image_path": str(png_path),
    }


def render_html_cards_for_items(
    question_text,
    items,
):
    """
    批量渲染多个错题卡。

    返回结构保持和旧 render_cards_for_items 一致：
    [
        {
            "index": 1,
            "question_text": "...",
            "item": {...},
            "image_path": "..."
        }
    ]
    """
    if not items:
        return []

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError(
            "未安装 Playwright，请先运行：pip install playwright && playwright install chromium"
        ) from e

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={
                "width": CARD_HTML_VIEWPORT_WIDTH,
                "height": CARD_HTML_VIEWPORT_HEIGHT,
            },
            device_scale_factor=1,
        )

        for index, item in enumerate(items, start=1):
            rendered = render_html_card_to_image_with_page(
                page=page,
                question_text=question_text,
                item=item,
            )

            results.append(
                {
                    "index": index,
                    "question_text": question_text,
                    "item": item,
                    "html_path": rendered.get("html_path", ""),
                    "image_path": rendered.get("image_path", ""),
                }
            )

        browser.close()

    return results