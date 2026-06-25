import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class LlmCalculationRoutingTests(unittest.TestCase):
    def test_calculation_is_not_a_tool_task(self):
        registry = load_module(
            "tool_registry_under_test",
            ROOT / "services" / "tools" / "tool_registry.py",
        )
        self.assertFalse(registry.is_tool_task("calculation"))
        self.assertTrue(registry.is_tool_task("log_query"))

    def test_calculation_never_requires_rag(self):
        validator = load_module(
            "task_validator_under_test",
            ROOT / "validators" / "task_validator.py",
        )
        result = validator.validate_task_info(
            {
                "task_type": "calculation",
                "need_rag": True,
                "answer_format": "数学解答",
                "reason": "test",
                "calculation_mode": "calculus",
                "math_request": {"expression": "x"},
            }
        )
        self.assertFalse(result["need_rag"])
        self.assertNotIn("calculation_mode", result)
        self.assertNotIn("math_request", result)

    def test_direct_prompt_contains_math_instructions(self):
        prompts = load_module(
            "direct_prompts_under_test",
            ROOT / "prompts" / "direct_prompts.py",
        )
        prompt = prompts.build_direct_answer_prompt(
            "求 x 从 0 到 1 的积分",
            "",
            {
                "task_type": "calculation",
                "reason": "test",
            },
        )
        self.assertIn("直接使用你的数学推理能力", prompt)
        self.assertIn("不定积分不要遗漏积分常数", prompt)


if __name__ == "__main__":
    unittest.main()
