import unittest

from services.exam_text_cleaner import normalize_exam_text


class ExamTextCleanerTest(unittest.TestCase):
    def test_splits_glued_options(self):
        text = "1. 下面正确的是：A. 选项一B. 选项二C. 选项三D. 选项四"

        cleaned = normalize_exam_text(text)

        self.assertIn("\nA.", cleaned)
        self.assertIn("\nB.", cleaned)
        self.assertIn("\nC.", cleaned)
        self.assertIn("\nD.", cleaned)

    def test_splits_inline_question_marker(self):
        text = "说明文字 1. 第一题内容 2. 第二题内容"

        cleaned = normalize_exam_text(text)

        self.assertIn("\n1.", cleaned)
        self.assertIn("\n2.", cleaned)

    def test_removes_standalone_url_line(self):
        text = "第1题 内容\nhttps://example.com/foo\n第2题 内容"

        cleaned = normalize_exam_text(text)

        self.assertNotIn("https://example.com", cleaned)

    def test_preserves_latex_spacing_inside_dollars(self):
        text = "第1题 计算 $P ( A ) = 0 . 5$  的值"

        cleaned = normalize_exam_text(text)

        self.assertIn("$P ( A ) = 0 . 5$", cleaned)


if __name__ == "__main__":
    unittest.main()
