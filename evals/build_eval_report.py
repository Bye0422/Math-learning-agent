import html
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "evals" / "eval_outputs"
SUMMARY_JSON_PATH = OUTPUT_DIR / "eval_summary_v2.json"
TREND_JSON_PATH = OUTPUT_DIR / "eval_trend_v2.json"
REPORT_HTML_PATH = OUTPUT_DIR / "eval_report_v2.html"


METRIC_LABELS = {
    "hit_rate": "Retrieval/answer hit score",
    "format_valid_rate": "Format valid rate",
    "elapsed_seconds_avg": "Average latency seconds",
    "rerank_usage_rate": "Rerank usage rate",
    "error_count": "Error count",
}


def load_json(path, default):
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def format_value(value):
    if value == "" or value is None:
        return "-"

    return html.escape(str(value), quote=False)


def build_metric_rows(latest, delta):
    rows = []

    for key, label in METRIC_LABELS.items():
        rows.append(
            f"""
            <tr>
              <td>{html.escape(label)}</td>
              <td>{format_value(latest.get(key, ""))}</td>
              <td>{format_value(delta.get(key, ""))}</td>
            </tr>
            """.strip()
        )

    return "\n".join(rows)


def build_history_rows(history):
    rows = []

    for item in reversed(history[-20:]):
        rows.append(
            f"""
            <tr>
              <td>{format_value(item.get("finished_at", ""))}</td>
              <td>{format_value(item.get("total_cases", ""))}</td>
              <td>{format_value(item.get("ok_cases", ""))}</td>
              <td>{format_value(item.get("skipped_cases", ""))}</td>
              <td>{format_value(item.get("hit_rate", ""))}</td>
              <td>{format_value(item.get("format_valid_rate", ""))}</td>
              <td>{format_value(item.get("elapsed_seconds_avg", ""))}</td>
              <td>{format_value(item.get("error_count", ""))}</td>
            </tr>
            """.strip()
        )

    return "\n".join(rows)


def build_eval_report_html(summary, trend_report):
    latest = trend_report.get("latest", {})
    delta = trend_report.get("delta", {})
    history = trend_report.get("history", [])

    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<title>Math-learning-agent Eval Report</title>
<style>
body {{
  margin: 32px;
  font-family: "Microsoft YaHei", Arial, sans-serif;
  color: #172033;
  background: #f7f8fb;
}}
h1, h2 {{
  margin: 0 0 16px 0;
}}
section {{
  margin: 0 0 28px 0;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
  border: 1px solid #d8dee9;
}}
th, td {{
  padding: 10px 12px;
  border-bottom: 1px solid #e5e9f0;
  text-align: left;
}}
th {{
  background: #eef2f7;
}}
.meta {{
  color: #526071;
  line-height: 1.7;
}}
</style>
</head>
<body>
  <h1>Math-learning-agent Eval Report</h1>

  <section class="meta">
    <div>Started: {format_value(summary.get("started_at", ""))}</div>
    <div>Finished: {format_value(summary.get("finished_at", ""))}</div>
    <div>Total cases: {format_value(summary.get("total_cases", ""))}</div>
    <div>OK cases: {format_value(summary.get("ok_cases", ""))}</div>
    <div>Skipped cases: {format_value(summary.get("skipped_cases", ""))}</div>
  </section>

  <section>
    <h2>Latest Metrics</h2>
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Latest</th>
          <th>Delta vs Previous</th>
        </tr>
      </thead>
      <tbody>
        {build_metric_rows(latest, delta)}
      </tbody>
    </table>
  </section>

  <section>
    <h2>Trend History</h2>
    <table>
      <thead>
        <tr>
          <th>Finished</th>
          <th>Total</th>
          <th>OK</th>
          <th>Skipped</th>
          <th>Hit</th>
          <th>Format</th>
          <th>Latency</th>
          <th>Errors</th>
        </tr>
      </thead>
      <tbody>
        {build_history_rows(history)}
      </tbody>
    </table>
  </section>
</body>
</html>
""".strip()


def write_eval_report(
    summary_path=SUMMARY_JSON_PATH,
    trend_path=TREND_JSON_PATH,
    output_path=REPORT_HTML_PATH,
):
    summary = load_json(Path(summary_path), {})
    trend_report = load_json(Path(trend_path), {})

    if not summary:
        raise FileNotFoundError(f"Missing summary JSON: {summary_path}")

    if not trend_report:
        trend_report = {
            "latest": {},
            "delta": {},
            "history": [],
        }

    html_text = build_eval_report_html(summary, trend_report)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def main():
    report_path = write_eval_report()
    print(f"Eval report written: {report_path}")


if __name__ == "__main__":
    main()
