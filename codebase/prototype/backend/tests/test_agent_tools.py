import unittest
from unittest.mock import patch

from core.agent_tools import execute_tool


PAGES = [
    (1, "LLM predicts the next token. Token is a unit of text."),
    (2, "Self-attention relates tokens to other tokens."),
    (3, "Evaluation uses a golden set and human review."),
]


class AgentToolTests(unittest.TestCase):
    @patch("core.agent_tools.db.get_pages", return_value=PAGES)
    def test_get_page_reads_only_existing_page(self, _):
        result = execute_tool("doc-1", "get_page", {"page_number": 2})
        self.assertEqual(result["page_number"], 2)
        with self.assertRaisesRegex(ValueError, "Page does not exist"):
            execute_tool("doc-1", "get_page", {"page_number": 99})

    @patch("core.agent_tools.db.get_pages", return_value=PAGES)
    def test_search_ranks_and_limits_matches(self, _):
        result = execute_tool("doc-1", "search_document", {"query": "token", "limit": 1})
        self.assertEqual([item["page_number"] for item in result["matches"]], [1])

    @patch("core.agent_tools.db.get_pages", return_value=[])
    def test_tools_fail_closed_for_unknown_document(self, _):
        with self.assertRaisesRegex(ValueError, "no ingested pages"):
            execute_tool("unknown", "get_document_index", {})


if __name__ == "__main__":
    unittest.main()
