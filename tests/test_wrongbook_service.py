import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from services import wrongbook_service


class WrongbookServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.db_path = self.tmp_path / "wrongbook.db"
        self.pdf_dir = self.tmp_path / "exports"

        self.patches = [
            patch.object(wrongbook_service, "WRONGBOOK_DB_PATH", str(self.db_path)),
            patch.object(wrongbook_service, "WRONGBOOK_PDF_OUTPUT_DIR", str(self.pdf_dir)),
        ]

        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()

        self.tmp.cleanup()

    def save_sample(self, session_id, question_text, analysis, difficulty, question_type, tags):
        return wrongbook_service.save_wrong_question(
            session_id=session_id,
            question_text=question_text,
            item={
                "analysis": analysis,
                "difficulty": difficulty,
                "type": question_type,
                "tags": tags,
            },
            card_image_path="",
            source_info={},
        )

    def test_filtered_wrong_questions(self):
        self.save_sample(
            session_id="s1",
            question_text="函数单调性题",
            analysis="导数判断单调性",
            difficulty=3,
            question_type="计算题",
            tags=["导数", "函数"],
        )
        self.save_sample(
            session_id="s1",
            question_text="概率选择题",
            analysis="古典概型",
            difficulty=2,
            question_type="选择题",
            tags=["概率"],
        )

        results = wrongbook_service.get_wrong_questions_filtered(
            session_id="s1",
            question_type="计算题",
            difficulty=3,
            tag="导数",
            keyword="单调性",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "计算题")
        self.assertIn("导数", results[0]["tags"])

    def test_get_wrong_questions_by_ids_preserves_order(self):
        first_id = self.save_sample("s1", "第一题", "解析1", 1, "填空题", ["代数"])
        second_id = self.save_sample("s1", "第二题", "解析2", 2, "计算题", ["函数"])

        results = wrongbook_service.get_wrong_questions_by_ids([second_id, first_id])

        self.assertEqual([item["id"] for item in results], [second_id, first_id])

    def test_export_wrong_questions_to_pdf_by_ids(self):
        image_path = self.tmp_path / "card.png"
        Image.new("RGB", (120, 160), "white").save(image_path)

        wrong_id = wrongbook_service.save_wrong_question(
            session_id="s1",
            question_text="题干",
            item={
                "analysis": "解析",
                "difficulty": 1,
                "type": "计算题",
                "tags": ["数学"],
            },
            card_image_path=str(image_path),
            source_info={},
        )

        pdf_path = wrongbook_service.export_wrong_questions_to_pdf_by_ids([wrong_id])

        self.assertTrue(Path(pdf_path).exists())
        self.assertGreater(Path(pdf_path).stat().st_size, 0)

    def test_wrongbook_review_columns_and_update(self):
        wrong_id = self.save_sample(
            "s1",
            "复习题",
            "解析",
            2,
            "计算题",
            ["函数"],
        )

        updated = wrongbook_service.update_wrong_question_review(
            wrong_id,
            mistake_reason="概念混淆",
            review_status="reviewing",
            next_review_at="2026-06-18",
            last_reviewed_at="2026-06-17",
        )

        self.assertTrue(updated)

        question = wrongbook_service.get_wrong_questions_by_ids([wrong_id])[0]
        self.assertEqual(question["mistake_reason"], "概念混淆")
        self.assertEqual(question["review_status"], "reviewing")
        self.assertEqual(question["next_review_at"], "2026-06-18")
        self.assertEqual(question["last_reviewed_at"], "2026-06-17")
        self.assertEqual(question["review_count"], 1)

        updated = wrongbook_service.update_wrong_question_review(
            wrong_id,
            last_reviewed_at="2026-06-18",
        )

        self.assertTrue(updated)

        question = wrongbook_service.get_wrong_questions_by_ids([wrong_id])[0]
        self.assertEqual(question["last_reviewed_at"], "2026-06-18")
        self.assertEqual(question["review_count"], 2)

    def test_filtered_wrong_questions_by_review_status_and_due_date(self):
        overdue_id = self.save_sample("s1", "过期错题", "解析", 2, "选择题", ["概率"])
        future_id = self.save_sample("s1", "未来错题", "解析", 2, "选择题", ["概率"])
        mastered_id = self.save_sample("s1", "已掌握错题", "解析", 2, "选择题", ["概率"])

        wrongbook_service.update_wrong_question_review(
            overdue_id,
            review_status="reviewing",
            next_review_at="2026-06-17",
        )
        wrongbook_service.update_wrong_question_review(
            future_id,
            review_status="reviewing",
            next_review_at="2026-06-20",
        )
        wrongbook_service.update_wrong_question_review(
            mastered_id,
            review_status="mastered",
            next_review_at="2026-06-16",
        )

        results = wrongbook_service.get_wrong_questions_filtered(
            session_id="s1",
            review_status="reviewing",
            due_before="2026-06-18",
        )

        self.assertEqual([item["id"] for item in results], [overdue_id])

    def test_get_wrongbook_review_summary(self):
        first_id = self.save_sample("s1", "第一题", "解析", 2, "计算题", ["函数"])
        second_id = self.save_sample("s1", "第二题", "解析", 2, "计算题", ["函数"])
        other_session_id = self.save_sample("s2", "其他会话", "解析", 2, "计算题", ["函数"])

        wrongbook_service.update_wrong_question_review(
            first_id,
            review_status="reviewing",
            next_review_at="2026-06-17",
            last_reviewed_at="2026-06-16",
        )
        wrongbook_service.update_wrong_question_review(
            first_id,
            last_reviewed_at="2026-06-17",
        )
        wrongbook_service.update_wrong_question_review(
            second_id,
            review_status="mastered",
            next_review_at="2026-06-20",
            last_reviewed_at="2026-06-17",
        )
        wrongbook_service.update_wrong_question_review(
            other_session_id,
            review_status="reviewing",
            next_review_at="2026-06-17",
            last_reviewed_at="2026-06-17",
        )

        summary = wrongbook_service.get_wrongbook_review_summary(
            session_id="s1",
            due_before="2026-06-18",
        )

        self.assertEqual(summary["by_status"], {"reviewing": 1, "mastered": 1})
        self.assertEqual(summary["due_count"], 1)
        self.assertEqual(summary["total_questions"], 2)
        self.assertEqual(summary["total_review_count"], 3)


if __name__ == "__main__":
    unittest.main()
