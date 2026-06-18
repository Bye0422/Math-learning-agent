import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.documents import Document

from services import correction_store_service


class CorrectionStoreServiceTest(unittest.TestCase):
    def test_save_and_apply_chunk_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "corrections.json"

            with patch.object(correction_store_service, "CORRECTION_STORE_PATH", store_path):
                correction_store_service.save_chunk_correction(
                    source="exam.pdf",
                    chunk_id=1,
                    corrected_text="修正后的题干",
                )
                chunks = [
                    Document(
                        page_content="原题干",
                        metadata={"source": "exam.pdf", "chunk_id": 1},
                    )
                ]

                corrected = correction_store_service.apply_chunk_corrections(chunks)

                self.assertEqual(corrected[0].page_content, "修正后的题干")
                self.assertTrue(corrected[0].metadata["chunk_corrected"])


if __name__ == "__main__":
    unittest.main()
