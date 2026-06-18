import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import memory_service


class MemoryServiceTest(unittest.TestCase):
    def test_save_qa_turn_writes_turn_and_chat_history(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "memory.db")

            with patch.object(memory_service, "MEMORY_DB_PATH", db_path):
                memory_service.init_memory_db()
                memory_service.save_qa_turn(
                    session_id="session-1",
                    question="question",
                    answer="answer",
                    file_key="file-key",
                    file_names=["doc.pdf"],
                    task_info={
                        "task_type": "qa",
                        "need_rag": True,
                        "answer_format": "plain",
                    },
                    route="rag",
                    retrieval_question="rewritten question",
                    top_k=3,
                    candidate_top_n=8,
                    rerank_used=True,
                    retrieved_sources=[{"source": "doc.pdf"}],
                    validation_result={"valid": True},
                    was_repaired=False,
                    elapsed_seconds=1.25,
                    error="",
                )

                turns = memory_service.get_session_turns("session-1")
                history = memory_service.load_chat_history("session-1")

        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["question"], "question")
        self.assertEqual(turns[0]["task_type"], "qa")
        self.assertEqual(turns[0]["need_rag"], "True")
        self.assertEqual(turns[0]["retrieved_sources"], [{"source": "doc.pdf"}])
        self.assertEqual(turns[0]["validation_result"], {"valid": True})
        self.assertEqual(
            history,
            [
                {"role": "user", "content": "question"},
                {"role": "assistant", "content": "answer"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
