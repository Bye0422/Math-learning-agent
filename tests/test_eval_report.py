import json
import tempfile
import unittest
from pathlib import Path

from evals.build_eval_report import METRIC_LABELS, write_eval_report


class EvalReportTest(unittest.TestCase):
    def test_write_eval_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            summary_path = tmp_path / "summary.json"
            trend_path = tmp_path / "trend.json"
            report_path = tmp_path / "report.html"

            summary_path.write_text(
                json.dumps(
                    {
                        "started_at": "2026-01-01 00:00:00",
                        "finished_at": "2026-01-01 00:01:00",
                        "total_cases": 2,
                        "ok_cases": 2,
                        "skipped_cases": 0,
                    }
                ),
                encoding="utf-8",
            )
            trend_path.write_text(
                json.dumps(
                    {
                        "latest": {
                            "hit_rate": 0.8,
                            "format_valid_rate": 1.0,
                            "elapsed_seconds_avg": 3.2,
                            "rerank_usage_rate": 1.0,
                            "error_count": 0,
                        },
                        "delta": {
                            "hit_rate": 0.1,
                        },
                        "history": [
                            {
                                "finished_at": "2026-01-01 00:01:00",
                                "total_cases": 2,
                                "ok_cases": 2,
                                "skipped_cases": 0,
                                "hit_rate": 0.8,
                                "format_valid_rate": 1.0,
                                "elapsed_seconds_avg": 3.2,
                                "error_count": 0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = write_eval_report(summary_path, trend_path, report_path)

            self.assertEqual(result, report_path)
            text = report_path.read_text(encoding="utf-8")
            self.assertIn("Math-learning-agent Eval Report", text)
            self.assertIn("Retrieval/answer hit score", text)
            self.assertIn("Trend History", text)
            for label in METRIC_LABELS.values():
                self.assertIn(label, text)

    def test_write_eval_report_escapes_html_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            summary_path = tmp_path / "summary.json"
            trend_path = tmp_path / "trend.json"
            report_path = tmp_path / "report.html"

            summary_path.write_text(
                json.dumps(
                    {
                        "started_at": '<script>alert("start")</script>',
                        "finished_at": "2026-01-01 00:01:00",
                        "total_cases": 1,
                        "ok_cases": 1,
                        "skipped_cases": 0,
                    }
                ),
                encoding="utf-8",
            )
            trend_path.write_text(
                json.dumps(
                    {
                        "latest": {
                            "hit_rate": "<b>0.8</b>",
                        },
                        "delta": {
                            "hit_rate": "<i>0.1</i>",
                        },
                        "history": [
                            {
                                "finished_at": "<img src=x onerror=alert(1)>",
                                "total_cases": 1,
                                "ok_cases": 1,
                                "skipped_cases": 0,
                                "hit_rate": "<b>0.8</b>",
                                "format_valid_rate": 1.0,
                                "elapsed_seconds_avg": 3.2,
                                "error_count": 0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            write_eval_report(summary_path, trend_path, report_path)

            text = report_path.read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;alert(\"start\")&lt;/script&gt;", text)
            self.assertIn("&lt;b&gt;0.8&lt;/b&gt;", text)
            self.assertIn("&lt;img src=x onerror=alert(1)&gt;", text)
            self.assertNotIn("<script>alert", text)
            self.assertNotIn("<b>0.8</b>", text)

    def test_write_eval_report_uses_recent_twenty_history_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            summary_path = tmp_path / "summary.json"
            trend_path = tmp_path / "trend.json"
            report_path = tmp_path / "report.html"

            summary_path.write_text(
                json.dumps(
                    {
                        "started_at": "start",
                        "finished_at": "finish",
                        "total_cases": 25,
                        "ok_cases": 25,
                        "skipped_cases": 0,
                    }
                ),
                encoding="utf-8",
            )
            history = [
                {
                    "finished_at": f"run-{index}",
                    "total_cases": index,
                    "ok_cases": index,
                    "skipped_cases": 0,
                    "hit_rate": 1.0,
                    "format_valid_rate": 1.0,
                    "elapsed_seconds_avg": 1.0,
                    "error_count": 0,
                }
                for index in range(25)
            ]
            trend_path.write_text(
                json.dumps(
                    {
                        "latest": history[-1],
                        "delta": {},
                        "history": history,
                    }
                ),
                encoding="utf-8",
            )

            write_eval_report(summary_path, trend_path, report_path)

            text = report_path.read_text(encoding="utf-8")
            self.assertIn("run-24", text)
            self.assertIn("run-5", text)
            self.assertNotIn("run-4", text)

    def test_write_eval_report_can_render_without_trend_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            summary_path = tmp_path / "summary.json"
            trend_path = tmp_path / "missing-trend.json"
            report_path = tmp_path / "report.html"

            summary_path.write_text(
                json.dumps(
                    {
                        "started_at": "start",
                        "finished_at": "finish",
                        "total_cases": 1,
                        "ok_cases": 1,
                        "skipped_cases": 0,
                    }
                ),
                encoding="utf-8",
            )

            write_eval_report(summary_path, trend_path, report_path)

            text = report_path.read_text(encoding="utf-8")
            self.assertIn("Latest Metrics", text)
            self.assertIn("<tbody>", text)


if __name__ == "__main__":
    unittest.main()
