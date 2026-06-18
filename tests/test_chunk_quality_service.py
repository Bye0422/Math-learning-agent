import unittest

from langchain_core.documents import Document

from services.chunk_quality_service import inspect_chunk_quality


class ChunkQualityServiceTest(unittest.TestCase):
    def test_detects_glued_options(self):
        chunk = Document(
            page_content="1. 下面正确的是：A. 选项一B. 选项二",
            metadata={"question_chunk": True, "question_marker": "1."},
        )

        result = inspect_chunk_quality(chunk)

        self.assertEqual(result["chunk_quality_level"], "high_risk")
        self.assertIn("选项疑似粘连", result["chunk_quality_issues"])

    def test_detects_multiple_questions_in_question_chunk(self):
        chunk = Document(
            page_content="1. 第一题\n2. 第二题",
            metadata={"question_chunk": True, "question_marker": "1."},
        )

        result = inspect_chunk_quality(chunk)

        self.assertIn("一个 chunk 内疑似包含多道题", result["chunk_quality_issues"])

    def test_ok_chunk_has_empty_issues(self):
        chunk = Document(
            page_content="1. 求函数值。\nA. 1\nB. 2\nC. 3\nD. 4",
            metadata={"question_chunk": True, "question_marker": "1."},
        )

        result = inspect_chunk_quality(chunk)

        self.assertEqual(result["chunk_quality_level"], "ok")
        self.assertEqual(result["chunk_quality_issues"], [])
        self.assertEqual(result["chunk_option_count"], 4)


if __name__ == "__main__":
    unittest.main()
