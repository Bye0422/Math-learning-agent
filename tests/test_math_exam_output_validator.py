import unittest

from validators.math_exam_output_validator import (
    parse_and_validate_math_exam_output,
    validate_math_exam_items,
)


class MathExamOutputValidatorTest(unittest.TestCase):
    def test_valid_choice_item(self):
        result = validate_math_exam_items(
            [
                {
                    "analysis": "选 A, 因为函数在该区间单调递增.",
                    "difficulty": 2,
                    "type": "选择题",
                    "tags": ["函数", "单调性"],
                }
            ]
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["items"][0]["difficulty"], 2)

    def test_invalid_choice_start_is_reported(self):
        result = validate_math_exam_items(
            [
                {
                    "analysis": "答案是 A, 因为函数在该区间单调递增.",
                    "difficulty": 2,
                    "type": "选择题",
                    "tags": ["函数"],
                }
            ]
        )

        self.assertFalse(result["valid"])
        self.assertTrue(any("选择题 analysis" in err for err in result["errors"]))

    def test_parse_json_object_with_items(self):
        text = """
        {
          "items": [
            {
              "analysis": "填 4, 将 x=2 代入表达式得到 4.",
              "difficulty": 1,
              "type": "填空题",
              "tags": ["代入求值"]
            }
          ]
        }
        """

        result = parse_and_validate_math_exam_output(text)
        self.assertTrue(result["valid"])
        self.assertEqual(result["items"][0]["type"], "填空题")


if __name__ == "__main__":
    unittest.main()
