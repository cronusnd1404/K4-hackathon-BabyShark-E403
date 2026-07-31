"""Prompt builders for deep explanations (mindmap node or highlighted text) and
per-slide practical exercises. These are now independent LLM calls (previously
one combined explanation+exercise prompt in the Streamlit version) -- product
decision: exercises are free-text-request-driven and persisted per-request,
not cached like node/highlight explanations.
"""

import hashlib
import json
import re
import uuid

from core import db
from core.llm_client import call_llm

JARGON_INSTRUCTION = (
    "Any term or concept that would likely be unfamiliar given the learner's "
    "stated background must be annotated inline the moment it is used (e.g. a "
    "short inline gloss in parentheses) -- do not assume familiarity beyond what "
    "their background indicates. This applies uniformly, not just to hard concepts."
)


def _system_prompt(background):
    return f"You are an AI tutor. The learner's background:\n{background}\n\n{JARGON_INSTRUCTION}"


def _format_page_index(page_index):
    return "\n".join(f"- Page {p['page_number']}: {p['title']}" for p in page_index)


def build_explain_prompt(background, target_content, page_index, user_question=None):
    """Explanation only -- no exercise. Returns (system_prompt, user_prompt)."""
    system = _system_prompt(background)
    question_block = f'\nThe learner also specifically asked: "{user_question}"\n' if user_question else ""
    user = f"""Explain the following content to the learner, integrating their background, general knowledge, and this material. Cite [Page X] when referencing specific pages.

Content to explain:
{target_content}
{question_block}
All pages in this document (for cross-referencing):
{_format_page_index(page_index)}

After the explanation, list which OTHER pages (not already part of the content above) are most related to this content and why, one line each. Omit the section entirely if truly nothing else is related.

Format your response EXACTLY as:
## Explanation
...

## Related Pages
- Page X: <one-line reason>
"""
    return system, user


def build_exercise_prompt(background, slide_content, user_request):
    """Exercise only -- no explanation. Returns (system_prompt, user_prompt)."""
    system = _system_prompt(background)
    user = f"""The learner asked for a practical exercise based on this slide's content, with this specific request: "{user_request}"

Slide content:
{slide_content}

Provide ONE practical exercise (5-10 minutes) addressing their request, using tools/languages appropriate for their background, with verifiable input/output.

Format:
## Practical Exercise: {{short title}}
**Objective:** ...
**Steps:** ...
**Expected Outcome:** ...
"""
    return system, user


def _parse_explanation_and_related(raw_text):
    marker = "## Related Pages"
    idx = raw_text.find(marker)
    if idx == -1:
        return raw_text.strip(), []
    explanation = raw_text[:idx].strip()
    related_block = raw_text[idx + len(marker):].strip()
    related_pages = []
    for line in related_block.splitlines():
        line = line.strip().lstrip("-").strip()
        if not line:
            continue
        page_part, _, reason = line.partition(":")
        reason = reason.strip()
        # A line can legitimately name more than one page (e.g. "Page 23, 25: ...");
        # extract each number separately rather than joining all digits into one
        # (which previously corrupted "23, 25" into the single bogus page 2325).
        for num in re.findall(r"\d+", page_part):
            related_pages.append({"page_number": int(num), "reason": reason})
    return explanation, related_pages


def build_page_index(document_id):
    """Compact (page_number, short title) index of every page -- lets the model
    name cross-page references. No per-page title exists anywhere in the schema,
    so the short title is always a ~10-word truncation of content_text."""
    pages = db.get_pages(document_id)
    index = []
    for page_number, content_text in pages:
        words = content_text.split()
        short = " ".join(words[:10]) + ("..." if len(words) > 10 else "")
        index.append({"page_number": page_number, "title": short})
    return index


def _collect_descendant_page_refs(node):
    refs = list(node.get("page_refs", []))
    for child in node.get("children") or []:
        refs.extend(_collect_descendant_page_refs(child))
    seen = set()
    ordered = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered


def explain_node(document_id, node, session_id, background, user_question=None):
    """A parent node's page_refs are the union of all its descendant leaves'
    page_refs, so the resulting explanation synthesizes across the whole branch
    rather than just describing that it has children."""
    cached = db.get_explanation(document_id, node["id"], session_id)
    if cached:
        explanation, related_json = cached
        return explanation, json.loads(related_json) if related_json else []

    page_refs = _collect_descendant_page_refs(node)
    all_pages = dict(db.get_pages(document_id))
    target_content = "\n\n".join(f"--- Page {p} ---\n{all_pages.get(p, '')}" for p in page_refs)
    page_index = build_page_index(document_id)

    system, user = build_explain_prompt(background, target_content, page_index, user_question)
    raw = call_llm(system, user, max_tokens=2048)
    explanation, related_pages = _parse_explanation_and_related(raw)
    # exercise_text column repurposed to hold related_pages_json -- see PHASE2_NOTES.md
    db.save_explanation(document_id, node["id"], session_id, explanation, json.dumps(related_pages))
    return explanation, related_pages


def explain_highlight(document_id, page_number, selected_text, session_id, background, user_question=None):
    text_hash = hashlib.sha256(selected_text.encode("utf-8")).hexdigest()[:16]
    cached = db.get_highlight_explanation(document_id, page_number, text_hash, session_id)
    if cached:
        explanation, related_json = cached
        return explanation, json.loads(related_json) if related_json else []

    all_pages = dict(db.get_pages(document_id))
    page_content = all_pages.get(page_number, "")
    target_content = f'Highlighted text: "{selected_text}"\n\nFull page {page_number} content for context:\n{page_content}'
    page_index = build_page_index(document_id)

    system, user = build_explain_prompt(background, target_content, page_index, user_question)
    raw = call_llm(system, user, max_tokens=2048)
    explanation, related_pages = _parse_explanation_and_related(raw)
    db.save_highlight_explanation(
        document_id, page_number, text_hash, session_id, selected_text, explanation, json.dumps(related_pages)
    )
    return explanation, related_pages


def generate_exercise(document_id, page_number, session_id, user_request, background):
    """Always generates fresh -- no cache check, since user_request is free-form."""
    all_pages = dict(db.get_pages(document_id))
    slide_content = all_pages.get(page_number, "")
    system, user = build_exercise_prompt(background, slide_content, user_request)
    exercise_text = call_llm(system, user, max_tokens=1024)
    exercise_id = str(uuid.uuid4())
    db.create_exercise(exercise_id, document_id, page_number, session_id, user_request, exercise_text)
    return exercise_id, exercise_text
