import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.llm_client import call_tool_agent


def block(block_type, **kwargs):
    return SimpleNamespace(type=block_type, **kwargs)


class ToolLoopTests(unittest.TestCase):
    def test_executes_tool_then_returns_final_text(self):
        responses = [
            SimpleNamespace(
                content=[
                    block(
                        "tool_use",
                        id="tool-1",
                        name="get_page",
                        input={"page_number": 2},
                    )
                ]
            ),
            SimpleNamespace(content=[block("text", text="Grounded answer [Page 2].")]),
        ]
        calls = []

        def execute(name, payload):
            calls.append((name, payload))
            return {"page_number": 2, "content": "verified"}

        with patch("core.llm_client._create_message", side_effect=responses) as create:
            result = call_tool_agent("system", "question", [], execute)

        self.assertEqual(result, "Grounded answer [Page 2].")
        self.assertEqual(calls, [("get_page", {"page_number": 2})])
        second_messages = create.call_args_list[1].args[0]["messages"]
        self.assertEqual(second_messages[-1]["content"][0]["type"], "tool_result")

    def test_tool_error_is_returned_to_model_not_raised(self):
        responses = [
            SimpleNamespace(
                content=[
                    block(
                        "tool_use",
                        id="tool-1",
                        name="get_page",
                        input={"page_number": 99},
                    )
                ]
            ),
            SimpleNamespace(content=[block("text", text="Không đủ dữ liệu.")]),
        ]

        def execute(_name, _payload):
            raise ValueError("Page does not exist")

        with patch("core.llm_client._create_message", side_effect=responses) as create:
            result = call_tool_agent("system", "question", [], execute)

        self.assertEqual(result, "Không đủ dữ liệu.")
        tool_result = create.call_args_list[1].args[0]["messages"][-1]["content"][0]
        self.assertTrue(tool_result["is_error"])


if __name__ == "__main__":
    unittest.main()
