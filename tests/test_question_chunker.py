import unittest

from langchain_core.documents import Document

from services.question_chunker import (
    find_question_markers,
    split_documents_by_questions,
    split_text_by_question_markers,
)
from services.vector_service import build_chunks_hash, split_documents


class QuestionChunkerTest(unittest.TestCase):
    def test_find_question_markers(self):
        text = "第1题 求函数值。\n第2题 判断单调性。\n③ 求概率。"
        markers = find_question_markers(text)

        self.assertEqual(len(markers), 3)
        self.assertEqual(markers[0]["marker"], "第1题")
        self.assertEqual(markers[1]["marker"], "第2题")
        self.assertEqual(markers[2]["marker"], "③")

    def test_split_text_by_question_markers(self):
        text = "说明文字\n第1题 求函数值。\nA. 选项\n第2题 判断单调性。"
        blocks = split_text_by_question_markers(text, min_markers=2)

        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0]["question_index"], 0)
        self.assertIn("第1题", blocks[1]["content"])
        self.assertIn("第2题", blocks[2]["content"])

    def test_split_documents_by_questions_preserves_metadata(self):
        doc = Document(
            page_content="第1题 求函数值。\n第2题 判断单调性。",
            metadata={
                "source": "exam.txt",
                "location": "全文",
            },
        )

        docs = split_documents_by_questions([doc], min_markers=2)

        self.assertEqual(len(docs), 2)
        self.assertTrue(docs[0].metadata["question_chunk"])
        self.assertEqual(docs[0].metadata["source"], "exam.txt")
        self.assertEqual(docs[1].metadata["question_index"], 2)

    def test_split_documents_uses_question_chunks_before_character_split(self):
        doc = Document(
            page_content="第1题 求函数值。\n第2题 判断单调性。",
            metadata={"source": "exam.txt", "location": "全文"},
        )

        chunks = split_documents([doc])

        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(chunks[0].metadata.get("question_chunk"))
        self.assertIn("chunk_id", chunks[0].metadata)

    def test_question_chunk_stays_intact_under_question_limit(self):
        long_question = "第1题 " + ("这是一道较长题干。" * 80)
        text = f"{long_question}\n第2题 判断单调性。"
        doc = Document(
            page_content=text,
            metadata={"source": "exam.txt", "location": "全文"},
        )

        chunks = split_documents([doc])

        self.assertEqual(chunks[0].metadata.get("question_marker"), "第1题")
        self.assertEqual(chunks[0].page_content, long_question)

    def test_split_documents_normalizes_exam_text_before_chunking(self):
        doc = Document(
            page_content="1. 下面正确的是：A. 选项一B. 选项二\n2. 第二题内容",
            metadata={"source": "exam.txt", "location": "全文"},
        )

        chunks = split_documents([doc])

        self.assertTrue(chunks[0].metadata.get("exam_text_cleaned"))
        self.assertIn("\nA.", chunks[0].page_content)
        self.assertIn("\nB.", chunks[0].page_content)
        self.assertEqual(chunks[0].metadata.get("chunk_quality_level"), "ok")

    def test_build_chunks_hash_is_stable(self):
        chunks = [
            Document(
                page_content="第1题",
                metadata={"source": "a.txt", "location": "p1", "chunk_id": 1},
            )
        ]

        self.assertEqual(build_chunks_hash(chunks), build_chunks_hash(chunks))


if __name__ == "__main__":
    unittest.main()
