import unittest

from services.tools.tool_registry import (
    get_tool_info,
    is_tool_task,
    list_available_tools,
    run_tool_by_task_type,
)


class ToolRegistryTest(unittest.TestCase):
    def test_registered_tools_are_discoverable(self):
        task_types = {tool["task_type"] for tool in list_available_tools()}

        self.assertIn("calculation", task_types)
        self.assertIn("log_query", task_types)
        self.assertTrue(is_tool_task("calculation"))
        self.assertEqual(get_tool_info("calculation")["tool_name"], "calculator_tool")

    def test_run_calculator_tool_without_llm(self):
        result = run_tool_by_task_type(
            "calculation",
            "2 * (3 + 4)",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["tool_name"], "calculator_tool")
        self.assertIn("14", result["answer"])
        self.assertEqual(result["metadata"]["task_type"], "calculation")

    def test_unsupported_tool_returns_structured_error(self):
        result = run_tool_by_task_type(
            "not_registered",
            "hello",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["tool_name"], "")
        self.assertIn("Unsupported tool task_type", result["error"])


if __name__ == "__main__":
    unittest.main()
