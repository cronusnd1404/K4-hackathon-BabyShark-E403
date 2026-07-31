"""Prompt + JSON parsing to build the hierarchical summary tree."""

import json
import os

from core import db
from core.llm_client import call_text

DEFAULT_SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tree.json")

TREE_PROMPT = """Based SOLELY on the content of the following pages from document {document_id}:
{pages_block}

Create a hierarchical summary tree (maximum 3 levels deep). Each node must contain:
- title
- one_liner (1 concise sentence, objective, NOT personalized)
- page_refs (list of specific page numbers)
- children

Return ONLY JSON adhering to this schema, with no additional text:
{{"tree": [{{"id": "", "title": "", "one_liner": "", "page_refs": [], "children": []}}]}}
"""


def _build_pages_block(pages):
    return "\n\n".join(f"--- Page {number} ---\n{text}" for number, text in pages)


def _assign_ids(nodes, prefix="n"):
    # Overwrite whatever id the LLM produced with a deterministic, guaranteed-unique
    # one -- needed as a stable cache/widget key for node_explanations and Streamlit.
    for i, node in enumerate(nodes):
        node["id"] = f"{prefix}{i}"
        children = node.get("children") or []
        node["children"] = children
        _assign_ids(children, prefix=f"{node['id']}-")


def _parse_tree_json(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[len("json"):]
    start = text.find("{")
    end = text.rfind("}")
    text = text[start:end + 1]
    return json.loads(text)["tree"]


def get_or_create_tree(document_id):
    cached = db.get_tree(document_id)
    if cached:
        return json.loads(cached)

    pages = db.get_pages(document_id)
    prompt = TREE_PROMPT.format(document_id=document_id, pages_block=_build_pages_block(pages))
    raw = call_text(system="You produce only valid JSON, no prose.", user_text=prompt, max_tokens=4096)
    tree = _parse_tree_json(raw)
    _assign_ids(tree)
    db.save_tree(document_id, json.dumps(tree))
    return tree


def find_node(tree_json, node_id):
    for node in tree_json:
        if node["id"] == node_id:
            return node
        found = find_node(node.get("children") or [], node_id)
        if found:
            return found
    return None


def _convert_node(node):
    children = node.get("children") or []
    return {
        "id": node["id"],
        "name": node["title"],
        "one_liner": node.get("one_liner", ""),
        "page_refs": node.get("page_refs", []),
        "is_leaf": not children,
        "children": [_convert_node(child) for child in children],
    }


def build_d3_tree(tree_json):
    """tree_json: list of top-level nodes -- same shape as st.session_state['tree']
    / data/sample_tree.json. Converts it to a single nested dict suitable for
    d3.hierarchy() on the JS side, wrapping under a synthetic root if there's more
    than one top-level node (d3.hierarchy needs exactly one root)."""
    converted = [_convert_node(node) for node in tree_json]
    if len(converted) == 1:
        return converted[0]
    return {
        "id": "__root__",
        "name": "Summary",
        "one_liner": "",
        "page_refs": [],
        "is_leaf": False,
        "children": converted,
    }


def export_tree_snapshot(document_id=None, output_path=None):
    """Dump a cached tree_json to a static file for UI-only iteration (no API calls)."""
    output_path = output_path or DEFAULT_SNAPSHOT_PATH

    if document_id is None:
        document_id = db.get_first_document_id()
        if document_id is None:
            raise RuntimeError("No cached summary tree found. Click 'Summarize Slides' at least once first.")

    tree_json = db.get_tree(document_id)
    if tree_json is None:
        raise RuntimeError(f"No cached tree for document_id={document_id!r}. Click 'Summarize Slides' first.")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(json.loads(tree_json), indent=2, ensure_ascii=False))
    return document_id, output_path
