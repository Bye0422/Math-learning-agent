import unittest

from services.tools.calculator_tool import (
    calculate_from_question,
    normalize_expression,
    safe_calculate,
)


class CalculatorToolTest(unittest.TestCase):
    def test_normalize_common_symbols(self):
        self.assertEqual(normalize_expression("请计算 2×3＋4"), "2*3＋4")
        self.assertEqual(normalize_expression("算一下 8÷2"), "8/2")
        self.assertEqual(normalize_expression("2^3"), "2**3")

    def test_safe_calculate_basic_expression(self):
        self.assertEqual(safe_calculate("2 + 3 * 4"), 14)
        self.assertEqual(safe_calculate("sqrt(16)"), 4)

    def test_rejects_unsafe_expression(self):
        with self.assertRaises(ValueError):
            safe_calculate("__import__('os').system('echo bad')")

    def test_calculate_from_question(self):
        result = calculate_from_question("请帮我计算 2 * (3 + 4)")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 14)


if __name__ == "__main__":
    unittest.main()
