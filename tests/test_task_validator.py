import unittest

from validators.task_validator import validate_task_info


class TaskValidatorTest(unittest.TestCase):
    def test_invalid_task_type_falls_back_to_qa(self):
        result = validate_task_info(
            {
                "task_type": "unknown",
                "need_rag": False,
                "answer_format": "",
                "reason": "",
            }
        )

        self.assertEqual(result["task_type"], "qa")
        self.assertTrue(result["need_rag"])
        self.assertEqual(result["answer_format"], "普通问答")

    def test_tool_task_does_not_need_rag(self):
        result = validate_task_info(
            {
                "task_type": "calculation",
                "need_rag": True,
                "answer_format": "计算",
                "reason": "用户要求计算",
            }
        )

        self.assertEqual(result["task_type"], "calculation")
        self.assertFalse(result["need_rag"])

if __name__ == "__main__":
    unittest.main()
