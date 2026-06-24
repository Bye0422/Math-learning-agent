import unittest

from services.vector_service import normalize_metadata_for_chroma


class VectorServiceTest(unittest.TestCase):
    def test_normalize_metadata_for_chroma_converts_empty_lists(self):
        metadata = {
            "source": "exam.png",
            "chunk_id": 1,
            "chunk_quality_issues": [],
            "tags": ["导数", "函数"],
            "extra": {"page": 1},
            "missing": None,
        }

        result = normalize_metadata_for_chroma(metadata)

        self.assertEqual(result["source"], "exam.png")
        self.assertEqual(result["chunk_id"], 1)
        self.assertEqual(result["chunk_quality_issues"], "")
        self.assertEqual(result["tags"], '["导数", "函数"]')
        self.assertEqual(result["extra"], '{"page": 1}')
        self.assertEqual(result["missing"], "")


if __name__ == "__main__":
    unittest.main()
