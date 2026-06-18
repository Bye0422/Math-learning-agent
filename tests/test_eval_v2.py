import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.documents import Document

from evals import run_eval_v2


class EvalV2Test(unittest.TestCase):
    def test_requires_docs_case_is_skipped_without_vector_db(self):
        result = run_eval_v2.evaluate_single_case(
            case={
                "case_id": "rag_case",
                "case_type": "rag",
                "question": "question",
                "requires_docs": True,
            },
            shared_context={
                "vector_db": None,
                "chunks": [],
            },
            chat_history=[],
        )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["retrieved_count"], "")

    def test_evaluate_single_case_extracts_metrics_from_graph_result(self):
        reranked_doc = Document(
            page_content="source keyword",
            metadata={
                "source": "doc.pdf",
                "_rerank_score": "4.5",
            },
        )

        fake_graph_result = {
            "task_info": {
                "task_type": "qa",
                "need_rag": True,
            },
            "answer": "answer keyword\nfield one",
            "route": "rag",
            "retrieval_question": "rewritten question",
            "retrieved_docs_with_scores": [(reranked_doc, 0.9)],
            "candidate_docs_with_scores": [(reranked_doc, 0.9), (reranked_doc, 0.4)],
            "validation_result": {"valid": True},
            "was_repaired": True,
            "rerank_used": True,
            "elapsed_seconds": 0.25,
            "error": "",
        }

        with patch.object(run_eval_v2, "run_agent_graph", return_value=fake_graph_result):
            chat_history = []
            result = run_eval_v2.evaluate_single_case(
                case={
                    "case_id": "case-1",
                    "case_type": "rag",
                    "question": "question",
                    "expected_task_type": "qa",
                    "expected_route": "rag",
                    "expected_need_rag": True,
                    "expected_answer_keywords": ["answer keyword"],
                    "expected_source_keywords": ["source keyword"],
                    "must_have_fields": ["field one"],
                },
                shared_context={
                    "vector_db": object(),
                    "chunks": [reranked_doc],
                },
                chat_history=chat_history,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["task_type_correct"], 1)
        self.assertEqual(result["route_correct"], 1)
        self.assertEqual(result["need_rag_correct"], 1)
        self.assertEqual(result["answer_keyword_score"], 1.0)
        self.assertEqual(result["source_keyword_score"], 1.0)
        self.assertEqual(result["must_have_fields_valid"], 1)
        self.assertEqual(result["retrieved_count"], 1)
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["rerank_used"], True)
        self.assertEqual(result["rerank_score_avg"], 4.5)
        self.assertEqual(result["format_valid"], True)
        self.assertEqual(result["was_repaired"], 1)
        self.assertEqual(len(chat_history), 2)

    def test_build_summary_and_trend_report(self):
        summary = run_eval_v2.build_summary(
            results=[
                {
                    "status": "ok",
                    "task_type_correct": 1,
                    "route_correct": 1,
                    "need_rag_correct": 1,
                    "answer_keyword_score": 0.5,
                    "source_keyword_score": 1.0,
                    "must_have_fields_valid": 1,
                    "format_valid": 1,
                    "was_repaired": 0,
                    "rerank_used": 1,
                    "rerank_score_avg": 4.0,
                    "retrieved_count": 3,
                    "candidate_count": 8,
                    "elapsed_seconds": 2.5,
                    "error": "",
                },
                {"status": "skipped"},
            ],
            doc_context={
                "source_files": ["doc.pdf"],
                "load_errors": [],
                "doc_stats": {"document_count": 1},
            },
            started_at="2026-01-01 00:00:00",
            finished_at="2026-01-01 00:00:03",
        )

        self.assertEqual(summary["total_cases"], 2)
        self.assertEqual(summary["ok_cases"], 1)
        self.assertEqual(summary["skipped_cases"], 1)
        self.assertEqual(summary["metrics"]["source_keyword_score_avg"], 1.0)
        self.assertEqual(summary["metrics"]["format_valid_rate"], 1.0)
        self.assertEqual(summary["metrics"]["elapsed_seconds_avg"], 2.5)
        self.assertEqual(summary["metrics"]["rerank_usage_rate"], 1.0)

        previous = {
            "started_at": "previous",
            "hit_rate": 0.75,
            "format_valid_rate": 0.5,
            "elapsed_seconds_avg": 3.0,
            "rerank_usage_rate": 0.0,
            "error_count": 1,
        }
        latest = run_eval_v2.build_trend_entry(summary)
        trend = run_eval_v2.build_trend_report([previous, latest])

        self.assertEqual(latest["hit_rate"], 1.0)
        self.assertEqual(latest["format_valid_rate"], 1.0)
        self.assertEqual(latest["elapsed_seconds_avg"], 2.5)
        self.assertEqual(latest["rerank_usage_rate"], 1.0)
        self.assertEqual(trend["delta"]["hit_rate"], 0.25)
        self.assertEqual(trend["delta"]["elapsed_seconds_avg"], -0.5)
        self.assertEqual(trend["delta"]["rerank_usage_rate"], 1.0)
        self.assertEqual(trend["delta"]["error_count"], -1.0)

    def test_summary_and_trend_keep_stable_tracking_fields(self):
        summary = run_eval_v2.build_summary(
            results=[
                {
                    "status": "ok",
                    "task_type_correct": 1,
                    "route_correct": 0,
                    "need_rag_correct": "",
                    "answer_keyword_score": 0.25,
                    "source_keyword_score": "",
                    "must_have_fields_valid": 0,
                    "format_valid": False,
                    "was_repaired": 1,
                    "rerank_used": False,
                    "rerank_score_avg": "",
                    "retrieved_count": 0,
                    "candidate_count": 5,
                    "elapsed_seconds": "1.25",
                    "error": "boom",
                }
            ],
            doc_context={
                "source_files": [],
                "load_errors": ["warn"],
                "doc_stats": {},
            },
            started_at="2026-01-01 00:00:00",
            finished_at="2026-01-01 00:00:02",
        )

        expected_metric_keys = {
            "task_type_accuracy",
            "route_accuracy",
            "need_rag_accuracy",
            "answer_keyword_score_avg",
            "source_keyword_score_avg",
            "must_have_fields_valid_rate",
            "format_valid_rate",
            "repair_trigger_rate",
            "rerank_usage_rate",
            "rerank_score_avg",
            "retrieved_count_avg",
            "candidate_count_avg",
            "elapsed_seconds_avg",
            "error_count",
        }
        self.assertEqual(set(summary["metrics"].keys()), expected_metric_keys)
        self.assertEqual(summary["metrics"]["error_count"], 1)
        self.assertEqual(summary["metrics"]["format_valid_rate"], 0.0)
        self.assertEqual(summary["metrics"]["repair_trigger_rate"], 1.0)

        trend_entry = run_eval_v2.build_trend_entry(summary)
        expected_trend_keys = {
            "started_at",
            "finished_at",
            "total_cases",
            "ok_cases",
            "skipped_cases",
            "hit_rate",
            "format_valid_rate",
            "elapsed_seconds_avg",
            "rerank_usage_rate",
            "error_count",
        }
        self.assertEqual(set(trend_entry.keys()), expected_trend_keys)
        self.assertEqual(trend_entry["hit_rate"], 0.25)
        self.assertEqual(trend_entry["error_count"], 1)

    def test_build_trend_entry_tolerates_invalid_error_count(self):
        trend_entry = run_eval_v2.build_trend_entry(
            {
                "started_at": "start",
                "finished_at": "finish",
                "total_cases": 1,
                "ok_cases": 1,
                "skipped_cases": 0,
                "metrics": {
                    "answer_keyword_score_avg": 0.75,
                    "error_count": "not-a-number",
                },
            }
        )

        self.assertEqual(trend_entry["hit_rate"], 0.75)
        self.assertEqual(trend_entry["error_count"], 0)

    def test_update_trend_report_appends_existing_history(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            trend_path = Path(tmp_dir) / "trend.json"
            trend_path.write_text(
                '{"history": [{"started_at": "old", "hit_rate": 0.5}]}',
                encoding="utf-8",
            )

            with patch.object(run_eval_v2, "TREND_JSON_PATH", trend_path):
                report = run_eval_v2.update_trend_report(
                    {
                        "started_at": "new",
                        "finished_at": "newer",
                        "total_cases": 1,
                        "ok_cases": 1,
                        "skipped_cases": 0,
                        "metrics": {
                            "source_keyword_score_avg": 1.0,
                            "format_valid_rate": 1.0,
                            "elapsed_seconds_avg": 1.0,
                            "rerank_usage_rate": 0.0,
                            "error_count": 0,
                        },
                    }
                )

        self.assertEqual(len(report["history"]), 2)
        self.assertEqual(report["latest"]["started_at"], "new")

    def test_update_trend_report_accepts_legacy_list_history(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            trend_path = Path(tmp_dir) / "trend.json"
            trend_path.write_text(
                '[{"started_at": "old", "hit_rate": 0.5}]',
                encoding="utf-8",
            )

            with patch.object(run_eval_v2, "TREND_JSON_PATH", trend_path):
                report = run_eval_v2.update_trend_report(
                    {
                        "started_at": "new",
                        "finished_at": "newer",
                        "total_cases": 1,
                        "ok_cases": 1,
                        "skipped_cases": 0,
                        "metrics": {
                            "answer_keyword_score_avg": 0.8,
                            "format_valid_rate": "",
                            "elapsed_seconds_avg": "",
                            "rerank_usage_rate": "",
                            "error_count": "",
                        },
                    }
                )

        self.assertEqual(len(report["history"]), 2)
        self.assertEqual(report["previous"]["started_at"], "old")
        self.assertEqual(report["latest"]["hit_rate"], 0.8)


if __name__ == "__main__":
    unittest.main()
