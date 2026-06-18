import unittest

from langchain_core.documents import Document

from services.question_parser_service import parse_question_from_chunk, parse_questions_from_chunks


class QuestionParserServiceTest(unittest.TestCase):
    def test_parse_choice_question(self):
        chunk = Document(
            page_content="1. 下列说法正确的是：\nA. 选项一\nB. 选项二\n答案：B\n解析：因为条件成立",
            metadata={
                "question_chunk": True,
                "question_marker": "1.",
                "chunk_id": 3,
                "source": "exam.pdf",
                "location": "题块 1",
            },
        )

        parsed = parse_question_from_chunk(chunk)

        self.assertEqual(parsed["question_number"], "1")
        self.assertEqual(parsed["options"]["A"], "选项一")
        self.assertEqual(parsed["options"]["B"], "选项二")
        self.assertEqual(parsed["answer"], "B")
        self.assertIn("因为条件成立", parsed["analysis"])

    def test_parse_questions_from_chunks_skips_regular_chunks(self):
        chunks = [
            Document(page_content="说明文字", metadata={}),
            Document(
                page_content="第2题 求概率。",
                metadata={"question_chunk": True, "question_marker": "第2题"},
            ),
        ]

        parsed = parse_questions_from_chunks(chunks)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["question_number"], "2")


if __name__ == "__main__":
    unittest.main()
