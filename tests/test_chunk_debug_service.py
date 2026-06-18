import unittest

from langchain_core.documents import Document

from services.chunk_debug_service import (
    build_chunk_debug_rows,
    filter_chunk_debug_rows,
)


class ChunkDebugServiceTest(unittest.TestCase):
    def test_build_rows_for_regular_chunk(self):
        chunks = [
            Document(
                page_content="  This is   a regular\n\nchunk.  ",
                metadata={
                    "chunk_id": 7,
                    "source": "lesson.pdf",
                    "location": "page 2",
                    "file_type": "pdf",
                    "chunk_quality_level": "ok",
                    "chunk_quality_issues": [],
                    "chunk_option_count": 0,
                    "chunk_question_marker_count": 0,
                },
            )
        ]

        rows = build_chunk_debug_rows(chunks)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["chunk_id"], 7)
        self.assertEqual(rows[0]["source"], "lesson.pdf")
        self.assertEqual(rows[0]["location"], "page 2")
        self.assertEqual(rows[0]["file_type"], "pdf")
        self.assertFalse(rows[0]["question_chunk"])
        self.assertEqual(rows[0]["question_marker"], "")
        self.assertEqual(rows[0]["question_index"], "")
        self.assertEqual(rows[0]["quality_level"], "ok")
        self.assertEqual(rows[0]["quality_issues"], "")
        self.assertEqual(rows[0]["char_count"], len(chunks[0].page_content))
        self.assertEqual(rows[0]["preview"], "This is a regular chunk.")

    def test_build_rows_for_question_chunk(self):
        chunks = [
            Document(
                page_content="Q1. Find x.\nA. 1\nB. 2",
                metadata={
                    "chunk_id": "q-1",
                    "source": "exam.txt",
                    "location": "full text | question block 1",
                    "file_type": "txt",
                    "question_chunk": True,
                    "question_marker": "Q1.",
                    "question_index": 1,
                    "chunk_quality_level": "warning",
                    "chunk_quality_issues": ["选项疑似粘连"],
                    "chunk_option_count": 2,
                    "chunk_question_marker_count": 1,
                    "exam_text_cleaned": True,
                    "chunk_corrected": True,
                },
            )
        ]

        rows = build_chunk_debug_rows(chunks)

        self.assertTrue(rows[0]["question_chunk"])
        self.assertEqual(rows[0]["question_marker"], "Q1.")
        self.assertEqual(rows[0]["question_index"], 1)
        self.assertEqual(rows[0]["quality_level"], "warning")
        self.assertEqual(rows[0]["quality_issues"], "选项疑似粘连")
        self.assertTrue(rows[0]["exam_text_cleaned"])
        self.assertTrue(rows[0]["chunk_corrected"])
        self.assertEqual(rows[0]["preview"], "Q1. Find x. A. 1 B. 2")

    def test_preview_is_truncated_after_whitespace_compaction(self):
        chunks = [
            Document(
                page_content="alpha\n\n" + ("beta " * 80),
                metadata={"source": "long.txt"},
            )
        ]

        rows = build_chunk_debug_rows(chunks, preview_length=20)

        self.assertLessEqual(len(rows[0]["preview"]), 20)
        self.assertTrue(rows[0]["preview"].endswith("…"))
        self.assertNotIn("\n", rows[0]["preview"])

    def test_filter_rows_by_keyword(self):
        rows = build_chunk_debug_rows(
            [
                Document(
                    page_content="derivative and tangent line",
                    metadata={"source": "calculus.pdf", "location": "page 4"},
                ),
                Document(
                    page_content="probability tree",
                    metadata={"source": "stats.pdf", "location": "page 8"},
                ),
            ]
        )

        self.assertEqual(
            [row["source"] for row in filter_chunk_debug_rows(rows, keyword="TANGENT")],
            ["calculus.pdf"],
        )
        self.assertEqual(
            [row["source"] for row in filter_chunk_debug_rows(rows, keyword="page 8")],
            ["stats.pdf"],
        )

    def test_filter_rows_by_question_marker(self):
        rows = build_chunk_debug_rows(
            [
                Document(
                    page_content="Q1. Find x.",
                    metadata={"question_chunk": True, "question_marker": "Q1.", "question_index": 1},
                ),
                Document(
                    page_content="Q2. Find y.",
                    metadata={"question_chunk": True, "question_marker": "Q2.", "question_index": 2},
                ),
                Document(page_content="regular chunk", metadata={}),
            ]
        )

        exact_rows = filter_chunk_debug_rows(rows, question_marker="Q1.")
        contains_rows = filter_chunk_debug_rows(rows, question_marker="2")

        self.assertEqual(len(exact_rows), 1)
        self.assertEqual(exact_rows[0]["question_index"], 1)
        self.assertEqual(len(contains_rows), 1)
        self.assertEqual(contains_rows[0]["question_marker"], "Q2.")


if __name__ == "__main__":
    unittest.main()
