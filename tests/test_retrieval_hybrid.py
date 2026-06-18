import unittest

from langchain_core.documents import Document

from services.retrieval_service import hybrid_retrieve


class FakeVectorDb:
    def __init__(self, results):
        self.results = results

    def similarity_search_with_score(self, query, k):
        return self.results[:k]


class HybridRetrievalTest(unittest.TestCase):
    def test_question_reference_rule_hit_can_outrank_vector_only_hit(self):
        exact_doc = Document(
            page_content="2. alpha exact question chunk",
            metadata={
                "source": "doc.pdf",
                "file_type": "txt",
                "location": "p2",
                "chunk_id": "exact",
            },
        )
        vector_only_doc = Document(
            page_content="unrelated semantic candidate",
            metadata={
                "source": "doc.pdf",
                "file_type": "txt",
                "location": "p1",
                "chunk_id": "vector",
            },
        )
        vector_db = FakeVectorDb([(vector_only_doc, 0.0)])

        results = hybrid_retrieve(
            vector_db=vector_db,
            chunks=[exact_doc, vector_only_doc],
            query="2. alpha",
            top_k=2,
        )

        self.assertEqual(results[0][0].metadata["chunk_id"], "exact")
        self.assertIn("rule", results[0][0].metadata["_retrieval_method"])
        self.assertGreater(
            results[0][0].metadata["_hybrid_score"],
            results[1][0].metadata["_hybrid_score"],
        )

    def test_original_query_preserves_question_number_for_rule_retrieval(self):
        exact_doc = Document(
            page_content="第2题 函数单调性问题，答案选B。",
            metadata={
                "source": "doc.pdf",
                "file_type": "txt",
                "location": "p2",
                "chunk_id": "exact",
            },
        )
        vector_doc = Document(
            page_content="函数单调性相关知识点",
            metadata={
                "source": "doc.pdf",
                "file_type": "txt",
                "location": "p1",
                "chunk_id": "vector",
            },
        )
        vector_db = FakeVectorDb([(vector_doc, 0.0)])

        results = hybrid_retrieve(
            vector_db=vector_db,
            chunks=[exact_doc, vector_doc],
            query="函数单调性问题",
            original_query="第2题为什么选B",
            top_k=2,
        )

        self.assertEqual(results[0][0].metadata["chunk_id"], "exact")
        self.assertEqual(results[0][0].metadata["_question_ref"]["question_number"], 2)
        self.assertEqual(results[0][0].metadata["_question_ref"]["option_letter"], "B")
        explanation = results[0][0].metadata["_retrieval_explanation"]
        self.assertEqual(explanation["question_ref"]["question_number"], 2)
        self.assertIn("rule", explanation["method"])
        self.assertIn("weights", explanation["hybrid"])
        self.assertTrue(explanation["rule"]["reasons"])


if __name__ == "__main__":
    unittest.main()
