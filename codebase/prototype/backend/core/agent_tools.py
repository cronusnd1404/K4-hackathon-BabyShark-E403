"""Read-only tools exposed to the tutor agent."""

import re

from core import db
from core.guardrails import MAX_PAGE_CONTENT_CHARS, clean_text


TOOL_DEFINITIONS = [
    {
        "name": "get_page",
        "description": "Read one page from the current ingested course document.",
        "input_schema": {
            "type": "object",
            "properties": {"page_number": {"type": "integer", "minimum": 1}},
            "required": ["page_number"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_document",
        "description": "Find pages in the current document containing terms relevant to a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2, "maxLength": 200},
                "limit": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_document_index",
        "description": "List page numbers and short previews for the current document.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def _pages_or_error(document_id):
    pages = db.get_pages(document_id)
    if not pages:
        raise ValueError("Document does not exist or has no ingested pages")
    return pages


def execute_tool(document_id, tool_name, tool_input):
    pages = _pages_or_error(document_id)
    page_map = dict(pages)

    if tool_name == "get_page":
        try:
            page_number = int(tool_input["page_number"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("page_number must be an integer") from exc
        if page_number not in page_map:
            raise ValueError("Page does not exist in current document")
        return {
            "page_number": page_number,
            "content": page_map[page_number][:MAX_PAGE_CONTENT_CHARS],
        }

    if tool_name == "get_document_index":
        return {
            "pages": [
                {"page_number": number, "preview": " ".join(text.split())[:240]}
                for number, text in pages
            ]
        }

    if tool_name == "search_document":
        query = clean_text(
            tool_input.get("query"),
            max_chars=200,
            field_name="query",
        )
        limit = max(1, min(int(tool_input.get("limit", 3)), 5))
        terms = {term for term in re.findall(r"\w+", query.casefold()) if len(term) > 1}
        if not terms:
            raise ValueError("query must contain searchable terms")
        matches = []
        for page_number, content in pages:
            normalized = content.casefold()
            score = sum(normalized.count(term) for term in terms)
            if score:
                matches.append(
                    {
                        "page_number": page_number,
                        "score": score,
                        "preview": " ".join(content.split())[:500],
                    }
                )
        matches.sort(key=lambda item: (-item["score"], item["page_number"]))
        return {"matches": matches[:limit]}

    raise ValueError(f"Unknown tool: {tool_name}")
