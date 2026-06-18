import unittest

from services.retrieval_service import (
    build_question_number_patterns,
    chinese_num_to_int,
    extract_question_reference,
    rule_retrieve,
)


class RetrievalServiceTest(unittest.TestCase):
    def test_chinese_num_to_int(self):
        self.assertEqual(chinese_num_to_int("一"), 1)
        self.assertEqual(chinese_num_to_int("十"), 10)
        self.assertEqual(chinese_num_to_int("十二"), 12)
        self.assertEqual(chinese_num_to_int("二十一"), 21)

    def test_extract_question_reference_with_type_and_number(self):
        result = extract_question_reference("选择题第二题为什么选 B")
        self.assertEqual(result["question_type"], "选择题")
        self.assertEqual(result["question_number"], 2)
        self.assertEqual(result["option_letter"], "B")

    def test_extract_question_reference_with_number_only(self):
        result = extract_question_reference("第 3 题怎么做")
        self.assertIsNone(result["question_type"])
        self.assertEqual(result["question_number"], 3)

    def test_build_question_number_patterns(self):
        patterns = build_question_number_patterns(2)
        self.assertIn("第2题", patterns)
        self.assertIn("第2小题", patterns)
        self.assertIn("第2问", patterns)
        self.assertIn("2.", patterns)
        self.assertIn("二、", patterns)

    def test_extract_question_reference_variants(self):
        cases = [
            ("第2小题怎么做", 2),
            ("第二问怎么做", 2),
            ("选择题2为什么错", 2),
            ("第（2）题", 2),
            ("② 这题怎么做", 2),
            ("第十二题", 12),
        ]

        for query, expected in cases:
            with self.subTest(query=query):
                result = extract_question_reference(query)
                self.assertEqual(result["question_number"], expected)

    def test_location_only_does_not_create_rule_candidate(self):
        from langchain_core.documents import Document

        doc = Document(
            page_content="完全无关的内容",
            metadata={
                "source": "doc.pdf",
                "location": "第 1 页",
                "chunk_id": "1",
            },
        )

        candidates, question_ref = rule_retrieve([doc], "第 2 题怎么做")

        self.assertEqual(candidates, [])
        self.assertEqual(question_ref["question_number"], 2)


if __name__ == "__main__":
    unittest.main()
